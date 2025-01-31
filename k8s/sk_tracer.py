import os

import fireconfig as fire
from cdk8s import Chart
from constructs import Construct
from fireconfig import k8s

ID = "sk-tracer"
SERVER_PORT = 7777
TRACER_CONFIG_YML = """---
trackedObjects:
  apps/v1.Deployment:
    podSpecTemplatePath: /spec/template
"""
CONFIGMAP_NAME = "tracer-config"


class SKTracer(Chart):
    def __init__(self, scope: Construct, namespace: str):
        super().__init__(scope, ID, disable_resource_name_hashes=True)

        app_key = "app"

        cm = k8s.KubeConfigMap(
            self, "configmap",
            metadata={"namespace": namespace},
            data={"tracer-config.yml": TRACER_CONFIG_YML}
        )

        env = fire.EnvBuilder({"RUST_BACKTRACE": "1"})
        volumes = fire.VolumesBuilder().with_config_map(CONFIGMAP_NAME, "/config", cm)

        try:
            with open(os.getenv('BUILD_DIR') + f'/{ID}-image') as f:
                image = f.read()
        except FileNotFoundError:
            image = 'PLACEHOLDER'

        container = fire.ContainerBuilder(
            name=ID,
            image=image,
            args=[
                "/sk-tracer",
                "--server-port", f"{SERVER_PORT}",
                "-c", volumes.get_path_to(CONFIGMAP_NAME),
            ],
        ).with_ports(SERVER_PORT).with_volumes(volumes).with_env(env)

        depl = (fire.DeploymentBuilder(namespace=namespace, selector={app_key: ID})
            .with_label(app_key, ID)
            .with_service_account_and_role_binding('cluster-admin', True)
            .with_containers(container)
            .with_service()
            .with_node_selector("type", "kind-worker")
        )
        depl.build(self)
