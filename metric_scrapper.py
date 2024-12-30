import time
from kubernetes import client, config

# Load kubeconfig
config.load_kube_config()

v1 = client.CoreV1Api()


def convert_cpu_usage(cpu_usage):
    # Convert nanocores to millicores (m)
    return int(cpu_usage[:-1]) / 1_000_000


def convert_memory_usage(memory_usage):
    # Convert Ki to MiB
    return int(memory_usage[:-2]) / 1024


def get_pod_metrics(namespace, pod_name):
    try:
        metrics = client.CustomObjectsApi().list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="pods"
        )

        for item in metrics['items']:
            if item['metadata']['name'] == pod_name:
                containers = item['containers']
                for container in containers:
                    name = container['name']
                    cpu_usage = container['usage']['cpu']
                    memory_usage = container['usage']['memory']

                    # Get resource requests
                    pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                    container_spec = next(c for c in pod.spec.containers if c.name == name)
                    cpu_request = container_spec.resources.requests['cpu']
                    memory_request = container_spec.resources.requests['memory']

                    # Convert requests to the same units as usage
                    cpu_request_m = int(cpu_request[:-1]) if cpu_request.endswith('m') else int(cpu_request) * 1000
                    memory_request_mib = int(memory_request[:-2]) / 1024 if memory_request.endswith('Ki') else int(
                        memory_request[:-2])

                    # Calculate usage percentages
                    cpu_usage_percentage = (convert_cpu_usage(cpu_usage) / cpu_request_m) * 100
                    memory_usage_percentage = (convert_memory_usage(memory_usage) / memory_request_mib) * 100
                    print(f"-------")
                    print(f"Container: {name}")
                    print(f"CPU Usage: {cpu_usage_percentage:.2f}% of {cpu_request}")
                    print(f"Memory Usage: {memory_usage_percentage:.2f}% of {memory_request}")
                    print(f"-------")
                    calculate_dynamic_requested_resource(namespace, pod_name, cpu_request_m, cpu_usage_percentage,
                                                         memory_request_mib, memory_usage_percentage)
    except Exception as e:
        print(f"Exception when calling CustomObjectsApi: {e}")


def update_pod_resources(namespace, pod_name, requested_cpu, requested_memory):
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        for container in pod.spec.containers:
            container.resources.requests['cpu'] = requested_cpu
            container.resources.requests['memory'] = requested_memory

        # Patch the pod with updated resources
        v1.patch_namespaced_pod(name=pod_name, namespace=namespace, body=pod)
        print(f"Updated pod {pod_name} with new resource requests: CPU={requested_cpu}, Memory={requested_memory}")
    except Exception as e:
        print(f"Exception when updating pod resources: {e}")


def update_pod_cpu_resources(namespace, pod_name, requested_cpu):
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        for container in pod.spec.containers:
            container.resources.requests['cpu'] = f"{requested_cpu}m"

        # Patch the pod with updated resources
        v1.patch_namespaced_pod(name=pod_name, namespace=namespace, body=pod)
        print(f"Updated pod {pod_name} with new resource requests: CPU={requested_cpu}")
    except Exception as e:
        print(f"Exception when updating pod resources: {e}")


def update_pod_memory_resources(namespace, pod_name, requested_memory):
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        for container in pod.spec.containers:
            container.resources.requests['memory'] = f"{requested_memory}Mi"

        # Patch the pod with updated resources
        v1.patch_namespaced_pod(name=pod_name, namespace=namespace, body=pod)
        print(f"Updated pod {pod_name} with new resource requests: Memory={requested_memory}")
    except Exception as e:
        print(f"Exception when updating pod resources: {e}")


def calculate_dynamic_requested_resource(namespace, pod_name, cpu_request, cpu_usage_percentage, memory_request,
                                         memory_usage_percentage):
   # print(f"cpu_usage_percentage {cpu_usage_percentage} cpu_request {cpu_request}")
    if cpu_usage_percentage > 70:
        update_pod_cpu_resources(namespace, pod_name, cpu_request * 1.1)
    if cpu_usage_percentage < 60:
        update_pod_cpu_resources(namespace, pod_name, cpu_request * 0.9)
    #print(f"mem_usage_percentage {memory_usage_percentage} mem_request {memory_request}")
    if memory_usage_percentage > 98:
        update_pod_memory_resources(namespace, pod_name, round(memory_request * 1.2))
    if memory_usage_percentage < 80:
        update_pod_memory_resources(namespace, pod_name, round(memory_request * 0.8))



def main():
    namespace = "default"
    pod_name = "demo-flask-prom-6f454b6cc4-5r5d6"
    # Periodically scrape metrics
    start_time = time.time()
    flag = False
    while True:
        get_pod_metrics(namespace, pod_name)
        time.sleep(5)  # Scrape every 5 seconds

        # Update resource requests after 30 seconds
        #if time.time() - start_time > 30 and flag == False:
        #   update_pod_resources(namespace, pod_name, '1000m', '200Mi')
        #   flag = True


if __name__ == "__main__":
    main()
