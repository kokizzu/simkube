import os

import fireconfig as fire
from cdk8s import Chart
from constructs import Construct
from fireconfig.types import Capability
from fireconfig.types import DownwardAPIField

ID = "sk-ctrl"


class SKController(Chart):
    def __init__(self, scope: Construct, namespace: str):
        super().__init__(scope, ID, disable_resource_name_hashes=True)

        app_key = "app"

        env = (fire.EnvBuilder({"RUST_BACKTRACE": "1"})
            .with_field_ref("POD_SVC_ACCOUNT", DownwardAPIField.SERVICE_ACCOUNT_NAME)
        )

        try:
            with open(os.getenv('BUILD_DIR') + f'/{ID}-image') as f:
                image = f.read()
        except FileNotFoundError:
            image = 'PLACEHOLDER'

        try:
            with open(os.getenv('BUILD_DIR') + '/sk-driver-image') as f:
                driver_image = f.read()
        except FileNotFoundError:
            driver_image = 'PLACEHOLDER'

        container = fire.ContainerBuilder(
            name=ID,
            image=image,
            args=[
                "/sk-ctrl",
                "--driver-image", driver_image,
                "--use-cert-manager",
                "--cert-manager-issuer", "selfsigned",
            ],
        ).with_security_context(Capability.DEBUG).with_env(env)

        depl = (fire.DeploymentBuilder(namespace=namespace, selector={app_key: ID})
            .with_label(app_key, ID)
            .with_service_account_and_role_binding('cluster-admin', True)
            .with_containers(container)
            .with_node_selector("type", "kind-worker")
        )
        depl.build(self)
