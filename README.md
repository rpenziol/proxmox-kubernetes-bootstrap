# PROXMOX KUBERNETES BOOTSTRAP

## Description
This is a collection of resources to get a Kubernetes cluster up and running in a Proxmox Virtual Environment. These tools and commands assume the user is executing in a Linux or Linux-like environment.
# Prerequisites

* Proxmox 6 or newer server up and running
* A set of RSA SSH keys generated (Specifically, a public key located at `$HOME/.ssh/id_rsa.pub`)
* Install Python 3
* [Install Docker](https://github.com/docker/docker-install#usage)
* Install Ansible and its dependencies

    ```bash
    python -m pip install -r ansible/requirements.txt
    exec bash --login  # Reload shell to add 'ansible-playbook' and 'ansible-galaxy' to your path
    ```

    Note: in some environments you may need to use `python3` instead of `python`
* Install Ansible collections

    ```bash
    ansible-galaxy install -r ansible/requirements.yml
    ```

# Create a VM template

## Copy the example configuration files

```bash
# From the repo's root path
cp ansible/group_vars/example-all.yml ansible/group_vars/all.yml
cp ansible/inventories/example-hosts.yml ansible/inventories/hosts.yml
cp ansible/inventories/example-proxmox.json ansible/inventories/proxmox.json
```

Fill in the `ansible/group_vars/all.yml`, `ansible/inventories/hosts.yml`, and `ansible/inventories/proxmox.json` files with values that are appropriate for your environment.

## Create your ubuntu-2004-server template

```bash
cd ansible # All the following steps assume you're in the 'ansible' directory. Ansible is directory dependant.
ansible-playbook proxmox_new_vm_template.yml -K
```

# Clone and prepare Kubernetes VMs

## Create Kubernetes control plane VMs

Note: All `ansible-playbook` commands should be run from the 'ansible' directory. Ansible is directory dependant.

```bash
# Use a for loop to create multiple systems. Set NUM_CONTROL_PLANE equal to the number of VMs you want.
#
# Minimum required: 1
# Kubespray requires an odd number of control plane nodes.
NUM_CONTROL_PLANE=1
for i in {1..${NUM_CONTROL_PLANE}} ; do ansible-playbook proxmox_k8s_new_master_vm.yml ; done
```

## Create Kubernetes node VMs

```bash
# Use a for loop to create multiple systems. Set NUM_NODES equal to the number of VMs you want.
#
# Minimum required: 1
NUM_NODES=1
for i in {1..${NUM_NODES}} ; do ansible-playbook proxmox_k8s_new_node_vm.yml ; done
```

## Prepare VMs

```bash
# Install 'sshpass' dependency locally for password authentication.
sudo apt-get install sshpass -y

ansible-playbook proxmox_vms_start_all.yml # Start all VMs. They automatically shutdown after being cloned.

ansible-playbook proxmox_k8s_vm_base_setup.yml -k # Ansible will prompt for a password. The default password defined in the template is 'ubuntu'
```

# Kubespray - Deploy Kubernetes

## (Optional, not recommended) Create kubespray Docker image

Note: This will pull the latest kubespray changes from GitHub, where the official kubespray Docker image may be months old

```bash
# This will take a few minutes
ansible-playbook kubespray_create_docker_image.yml
```

## Copy sample inventory files

```bash
# Run this command if you did the optional step above and wish to use the latest kubespray updates (not recommended)
DOCKER_IMAGE=kubespray_github
# Run this command if you wish to use the official kubespray Docker image (recommended)
DOCKER_IMAGE=quay.io/kubespray/kubespray:v2.19.1

CID=$(docker create ${DOCKER_IMAGE})
docker cp ${CID}:/kubespray/inventory/sample mycluster
docker rm ${CID}
```

Make any desired modifications to the files in "mycluster"

## Run deploy

```bash
docker run --name kubespray -d -t \
    -v $(pwd)/mycluster:/kubespray/inventory/mycluster \
    -v $(pwd)/inventories/proxmox.json:/kubespray/inventory/mycluster/proxmox.json \
    -v $(pwd)/inventories/proxmox.py:/kubespray/inventory/mycluster/proxmox.py \
    -v $HOME/.ssh/id_rsa:/root/.ssh/id_rsa \
    ${DOCKER_IMAGE}

docker exec -it kubespray ansible-playbook -i inventory/mycluster/proxmox.py --user=ubuntu --become --become-user=root cluster.yml
```

# kubectl - Manager your Kubernetes cluster - WIP

## Authorization

```bash
mkdir -p $HOME/.kube

IP=192.168.1.133  # Master node IP address

ssh ubuntu@${IP} 'mkdir -p $HOME/.kube && sudo cp -f /etc/kubernetes/admin.conf $HOME/.kube/config'

ssh ubuntu@${IP} 'sudo cat $HOME/.kube/config' > $HOME/.kube/config

sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

## Dashboard Tokens

```bash
kubectl create serviceaccount dashboard -n default

kubectl create clusterrolebinding dashboard-admin -n default --clusterrole=cluster-admin --serviceaccount=default:dashboard

kubectl get secret $(kubectl get serviceaccount dashboard -o jsonpath="{.secrets[0].name}") -o jsonpath="{.data.token}" | base64 --decode
```

## Dummy deploy

```bash
kubectl run kubia --image=luksa/kubia --port=8080

kubectl expose pod kubia --type=LoadBalancer --name kubia-http

kubectl get services

kubectl proxy
```

# Proxmox CLI cheat sheet - Potentially useful commands

Note: These commands must be run on the Proxmox host as root

## Snapshot commands

```bash
qm list | grep running | awk '{print $1}' | xargs -I {} qm snapshot {} base --vmstate true
qm list | grep running | awk '{print $1}' | xargs -I {} qm rollback {} base
qm list | awk '{print $1}' | grep [0-9] | xargs -i sh -c "qm start {} || true"
```
