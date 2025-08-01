# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import tempfile

from ops import ActiveStatus, BlockedStatus, WaitingStatus, testing
from ops.pebble import Layer, ServiceStatus

from tests.unit.certificates_helpers import (
    example_cert_and_key,
)
from tests.unit.fixtures import AMFUnitTestFixtures


class TestCharmCollectUnitStatus(AMFUnitTestFixtures):
    def test_given_invalid_log_level_config_when_collect_unit_status_then_status_is_blocked(
        self,
    ):
        container = testing.Container(name="amf", can_connect=True)
        state_in = testing.State(
            leader=True,
            config={"log-level": "invalid"},
            containers={container},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == BlockedStatus(
            "The following configurations are not valid: ['log-level']"
        )

    def test_given_fiveg_nrf_relation_not_created_when_collect_unit_status_then_status_is_blocked(
        self,
    ):
        certificates_relation = testing.Relation(
            endpoint="certificates", interface="tls-certificates"
        )
        sdcore_config_relation = testing.Relation(
            endpoint="sdcore_config", interface="sdcore_config"
        )
        container = testing.Container(name="amf", can_connect=True)
        state_in = testing.State(
            leader=True,
            containers={container},
            relations={certificates_relation, sdcore_config_relation},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == BlockedStatus("Waiting for fiveg_nrf relation(s)")

    def test_given_certificates_relation_not_created_when_collect_unit_status_then_status_is_blocked(  # noqa: E501
        self,
    ):
        nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
        sdcore_config_relation = testing.Relation(
            endpoint="sdcore_config", interface="sdcore_config"
        )
        container = testing.Container(name="amf", can_connect=True)
        state_in = testing.State(
            leader=True,
            containers={container},
            relations={nrf_relation, sdcore_config_relation},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == BlockedStatus("Waiting for certificates relation(s)")

    def test_given_sdcore_config_relation_not_created_when_collect_unit_status_then_status_is_blocked(  # noqa: E501
        self,
    ):
        nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
        certificates_relation = testing.Relation(
            endpoint="certificates", interface="tls-certificates"
        )
        container = testing.Container(name="amf", can_connect=True)
        state_in = testing.State(
            leader=True,
            containers={container},
            relations={nrf_relation, certificates_relation},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == BlockedStatus("Waiting for sdcore_config relation(s)")

    def test_given_nrf_data_not_available_when_collect_unit_status_then_status_is_waiting(
        self,
    ):
        certificates_relation = testing.Relation(
            endpoint="certificates", interface="tls-certificates"
        )
        sdcore_config_relation = testing.Relation(
            endpoint="sdcore_config", interface="sdcore_config"
        )
        nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
        container = testing.Container(name="amf", can_connect=True)
        state_in = testing.State(
            leader=True,
            containers={container},
            relations={
                certificates_relation,
                sdcore_config_relation,
                nrf_relation,
            },
        )
        self.mock_nrf_url.return_value = ""

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for NRF data to be available")

    def test_given_webui_data_not_available_when_collect_unit_status_then_status_is_waiting(
        self,
    ):
        nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
        certificates_relation = testing.Relation(
            endpoint="certificates", interface="tls-certificates"
        )
        sdcore_config_relation = testing.Relation(
            endpoint="sdcore_config", interface="sdcore_config"
        )
        container = testing.Container(name="amf", can_connect=True)
        state_in = testing.State(
            leader=True,
            containers={container},
            relations={
                nrf_relation,
                certificates_relation,
                sdcore_config_relation,
            },
        )
        self.mock_webui_url.return_value = ""
        self.mock_nrf_url.return_value = "http://nrf"

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for Webui data to be available")

    def test_given_storage_not_attached_when_collect_unit_status_then_status_is_waiting(
        self,
    ):
        nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
        certificates_relation = testing.Relation(
            endpoint="certificates", interface="tls-certificates"
        )
        sdcore_config_relation = testing.Relation(
            endpoint="sdcore_config", interface="sdcore_config"
        )
        container = testing.Container(name="amf", can_connect=True)
        state_in = testing.State(
            leader=True,
            containers={container},
            relations={
                nrf_relation,
                certificates_relation,
                sdcore_config_relation,
            },
        )
        self.mock_nrf_url.return_value = "http://nrf"

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for storage to be attached")

    def test_given_certificates_not_stored_when_collect_unit_status_then_status_is_waiting(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
            sdcore_config_relation = testing.Relation(
                endpoint="sdcore_config", interface="sdcore_config"
            )
            certificates_relation = testing.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            config_mount = testing.Mount(
                location="/free5gc/config",
                source=tempdir,
            )
            container = testing.Container(
                name="amf", can_connect=True, mounts={"config": config_mount}
            )
            state_in = testing.State(
                leader=True,
                containers={container},
                relations={
                    nrf_relation,
                    certificates_relation,
                    sdcore_config_relation,
                },
            )
            self.mock_get_assigned_certificate.return_value = None, None
            self.mock_check_output.return_value = b"192.0.2.1"
            self.mock_nrf_url.return_value = "http://nrf"

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == WaitingStatus(
                "Waiting for certificates to be available"
            )

    def test_relations_available_and_config_pushed_and_pebble_updated_when_collect_unit_status_then_status_is_active(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
            certificates_relation = testing.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            sdcore_config_relation = testing.Relation(
                endpoint="sdcore_config", interface="sdcore_config"
            )
            certs_mount = testing.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            config_mount = testing.Mount(
                location="/free5gc/config",
                source=tempdir,
            )
            container = testing.Container(
                name="amf",
                layers={
                    "amf": Layer(
                        {
                            "services": {
                                "amf": {
                                    "startup": "enabled",
                                    "override": "replace",
                                    "command": "/bin/amf --amfcfg /free5gc/config/amfcfg.conf",
                                    "environment": {
                                        "GOTRACEBACK": "crash",
                                        "POD_IP": "192.0.2.1",
                                        "MANAGED_BY_CONFIG_POD": "true",
                                    },
                                }
                            }
                        }
                    )
                },
                can_connect=True,
                mounts={"certs": certs_mount, "config": config_mount},
                service_statuses={"amf": ServiceStatus.ACTIVE},
            )
            state_in = testing.State(
                leader=True,
                containers={container},
                relations={
                    nrf_relation,
                    certificates_relation,
                    sdcore_config_relation,
                },
            )
            provider_certificate, private_key = example_cert_and_key(
                tls_relation_id=certificates_relation.id
            )
            self.mock_get_assigned_certificate.return_value = provider_certificate, private_key
            self.mock_check_output.return_value = b"192.0.2.1"
            self.mock_nrf_url.return_value = "http://nrf"

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == ActiveStatus()

    def test_unit_is_non_leader_when_collect_unit_status_then_status_is_active(self):
        state_in = testing.State(
            leader=False
        )
        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == ActiveStatus("standby (non-leader)")

    def test_given_empty_ip_address_when_collect_unit_status_then_status_is_waiting(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
            certificates_relation = testing.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            sdcore_config_relation = testing.Relation(
                endpoint="sdcore_config", interface="sdcore_config"
            )
            certs_mount = testing.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            config_mount = testing.Mount(
                location="/free5gc/config",
                source=tempdir,
            )
            container = testing.Container(
                name="amf", can_connect=True, mounts={"certs": certs_mount, "config": config_mount}
            )
            state_in = testing.State(
                leader=True,
                containers={container},
                relations={
                    nrf_relation,
                    certificates_relation,
                    sdcore_config_relation,
                },
            )
            self.mock_check_output.return_value = b""
            self.mock_nrf_url.return_value = "http://nrf"

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == WaitingStatus(
                "Waiting for pod IP address to be available"
            )

    def test_given_no_workload_version_file_when_collect_unit_status_then_workload_version_not_set(
        self,
    ):
        nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
        certificates_relation = testing.Relation(
            endpoint="certificates", interface="tls-certificates"
        )
        sdcore_config_relation = testing.Relation(
            endpoint="sdcore_config", interface="sdcore_config"
        )
        container = testing.Container(name="amf", can_connect=True)
        state_in = testing.State(
            leader=True,
            containers={container},
            relations={nrf_relation, certificates_relation, sdcore_config_relation},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.workload_version == ""

    def test_given_workload_version_file_when_collect_unit_status_then_workload_version_set(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
            certificates_relation = testing.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            sdcore_config_relation = testing.Relation(
                endpoint="sdcore_config", interface="sdcore_config"
            )
            workload_version_mount = testing.Mount(
                location="/etc",
                source=tempdir,
            )
            # Write workload version file
            expected_version = "1.2.3"
            with open(f"{tempdir}/workload-version", "w") as f:
                f.write(expected_version)
            container = testing.Container(
                name="amf", can_connect=True, mounts={"workload-version": workload_version_mount}
            )
            state_in = testing.State(
                leader=True,
                containers={container},
                relations={nrf_relation, certificates_relation, sdcore_config_relation},
            )

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.workload_version == expected_version

    def test_given_n2_information_and_service_is_running_and_metallb_service_is_not_available_when_collect_unit_status_then_amf_goes_in_blocked_state(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            nrf_relation = testing.Relation(endpoint="fiveg_nrf", interface="fiveg_nrf")
            certificates_relation = testing.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            sdcore_config_relation = testing.Relation(
                endpoint="sdcore_config", interface="sdcore_config"
            )
            fiveg_n2_relation = testing.Relation(endpoint="fiveg-n2", interface="fiveg-n2")
            config_mount = testing.Mount(
                location="/free5gc/config",
                source=tempdir,
            )
            certs_mount = testing.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = testing.Container(
                name="amf",
                can_connect=True,
                mounts={"certs": certs_mount, "config": config_mount},
                layers={
                    "amf": Layer(
                        {
                            "services": {
                                "amf": {
                                    "startup": "enabled",
                                    "override": "replace",
                                    "command": "/bin/amf --amfcfg /free5gc/config/amfcfg.conf",
                                    "environment": {
                                        "GOTRACEBACK": "crash",
                                        "POD_IP": "192.0.2.1",
                                        "MANAGED_BY_CONFIG_POD": "true",
                                    },
                                }
                            }
                        }
                    )
                },
                service_statuses={"amf": ServiceStatus.ACTIVE},
            )
            state_in = testing.State(
                leader=True,
                containers={container},
                relations={
                    fiveg_n2_relation,
                    nrf_relation,
                    certificates_relation,
                    sdcore_config_relation,
                },
            )
            self.mock_check_output.return_value = b"192.0.2.1"
            self.mock_k8s_service.get_hostname.return_value = None
            self.mock_k8s_service.get_ip.return_value = None
            self.mock_nrf_url.return_value = "http://nrf"

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == BlockedStatus("Waiting for MetalLB to be enabled")
