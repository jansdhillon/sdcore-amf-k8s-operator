#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
import getpass
import logging
from pathlib import Path

import pytest
import yaml
from pytest_operator.plugin import OpsTest

from tests.integration.jhack_helper import JhackClient

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]
DB_CHARM_NAME = "mongodb-k8s"
DB_CHARM_CHANNEL = "6/edge"
NRF_CHARM_NAME = "sdcore-nrf-k8s"
NRF_CHARM_CHANNEL = "1.6/edge"
TLS_PROVIDER_CHARM_NAME = "self-signed-certificates"
TLS_PROVIDER_CHARM_CHANNEL = "latest/stable"
NMS_CHARM_NAME = "sdcore-nms-k8s"
NMS_CHARM_CHANNEL = "1.6/edge"
GRAFANA_AGENT_CHARM_NAME = "grafana-agent-k8s"
GRAFANA_AGENT_CHARM_CHANNEL = "1/stable"
SDCORE_CHARMS_BASE = "ubuntu@24.04"
TIMEOUT = 15 * 60


@pytest.fixture(scope="module")
async def deploy(ops_test: OpsTest, request):
    """Deploy the charm-under-test."""
    assert ops_test.model
    charm = Path(request.config.getoption("--charm_path")).resolve()
    resources = {
        "amf-image": METADATA["resources"]["amf-image"]["upstream-source"],
    }
    await ops_test.model.deploy(
        charm,
        resources=resources,
        application_name=APP_NAME,
        trust=True,
    )
    await _deploy_self_signed_certificates(ops_test)
    await _deploy_mongodb(ops_test)
    await _deploy_nms(ops_test)
    await _deploy_nrf(ops_test)
    await _deploy_grafana_agent(ops_test)


@pytest.mark.abort_on_fail
async def test_deploy_charm_and_wait_for_blocked_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="blocked",
        timeout=TIMEOUT,
    )


@pytest.mark.abort_on_fail
async def test_relate_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model

    await ops_test.model.integrate(relation1=APP_NAME, relation2=NRF_CHARM_NAME)
    await ops_test.model.integrate(relation1=APP_NAME, relation2=NMS_CHARM_NAME)
    await ops_test.model.integrate(relation1=APP_NAME, relation2=TLS_PROVIDER_CHARM_NAME)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:logging", relation2=f"{GRAFANA_AGENT_CHARM_NAME}:logging-provider"
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="active",
        timeout=TIMEOUT,
    )


@pytest.mark.abort_on_fail
async def test_remove_nrf_and_wait_for_blocked_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await ops_test.model.remove_application(NRF_CHARM_NAME, block_until_done=True)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="blocked", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_restore_nrf_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await _deploy_nrf(ops_test)
    await ops_test.model.integrate(relation1=APP_NAME, relation2=NRF_CHARM_NAME)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_remove_tls_and_wait_for_blocked_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await ops_test.model.remove_application(TLS_PROVIDER_CHARM_NAME, block_until_done=True)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="blocked", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_restore_tls_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await _deploy_self_signed_certificates(ops_test)
    await ops_test.model.integrate(relation1=APP_NAME, relation2=TLS_PROVIDER_CHARM_NAME)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_remove_nms_and_wait_for_blocked_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await ops_test.model.remove_application(NMS_CHARM_NAME, block_until_done=True)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="blocked", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_restore_nms_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await _deploy_nms(ops_test)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:sdcore_config", relation2=f"{NMS_CHARM_NAME}:sdcore_config"
    )
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_scale_up_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    amf_app = ops_test.model.applications.get(APP_NAME)
    assert amf_app
    await amf_app.scale(2)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_trigger_leader_election_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    current_model = ops_test.model.name
    jhack_client = JhackClient(model=current_model, user=getpass.getuser())
    jhack_client.elect(application=APP_NAME, unit_id=1)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)
    expected_leader_unit = ops_test.model.units.get(f"{APP_NAME}/1")
    assert expected_leader_unit
    assert await expected_leader_unit.is_leader_from_status()


@pytest.mark.abort_on_fail
async def test_scale_down_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    amf_app = ops_test.model.applications.get(APP_NAME)
    assert amf_app
    await amf_app.scale(1)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)
    expected_leader_unit = ops_test.model.units.get(f"{APP_NAME}/0")
    assert expected_leader_unit
    assert await expected_leader_unit.is_leader_from_status()


async def _deploy_mongodb(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        DB_CHARM_NAME,
        application_name=DB_CHARM_NAME,
        channel=DB_CHARM_CHANNEL,
        trust=True,
    )


async def _deploy_grafana_agent(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        GRAFANA_AGENT_CHARM_NAME,
        application_name=GRAFANA_AGENT_CHARM_NAME,
        channel=GRAFANA_AGENT_CHARM_CHANNEL,
    )


async def _deploy_self_signed_certificates(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        TLS_PROVIDER_CHARM_NAME,
        application_name=TLS_PROVIDER_CHARM_NAME,
        channel=TLS_PROVIDER_CHARM_CHANNEL,
    )


async def _deploy_nrf(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        NRF_CHARM_NAME,
        application_name=NRF_CHARM_NAME,
        channel=NRF_CHARM_CHANNEL,
        base=SDCORE_CHARMS_BASE,
    )
    await ops_test.model.integrate(
        relation1=f"{NRF_CHARM_NAME}:database", relation2=f"{DB_CHARM_NAME}"
    )
    await ops_test.model.integrate(relation1=NRF_CHARM_NAME, relation2=TLS_PROVIDER_CHARM_NAME)
    await ops_test.model.integrate(relation1=NRF_CHARM_NAME, relation2=NMS_CHARM_NAME)


async def _deploy_nms(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        NMS_CHARM_NAME,
        application_name=NMS_CHARM_NAME,
        channel=NMS_CHARM_CHANNEL,
        base=SDCORE_CHARMS_BASE,
    )
    await ops_test.model.integrate(
        relation1=f"{NMS_CHARM_NAME}:common_database", relation2=f"{DB_CHARM_NAME}"
    )
    await ops_test.model.integrate(
        relation1=f"{NMS_CHARM_NAME}:auth_database", relation2=f"{DB_CHARM_NAME}"
    )
    await ops_test.model.integrate(
        relation1=f"{NMS_CHARM_NAME}:webui_database", relation2=f"{DB_CHARM_NAME}"
    )
    await ops_test.model.integrate(relation1=NMS_CHARM_NAME, relation2=TLS_PROVIDER_CHARM_NAME)
