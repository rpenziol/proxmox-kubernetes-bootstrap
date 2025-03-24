# PROXMOX KUBERNETES BOOTSTRAP

## Description
This is a collection of resources to get a Kubernetes cluster up and running in a Proxmox Virtual Environment. These tools and commands assume the user is executing in a Linux or Linux-like environment.
# Prerequisites

* Proxmox 8 or newer server up and running
* Install Python 3 (Comes pre-installed on most Linux distros)
* [Generate a set of SSH keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key)
* [Install Docker](https://github.com/docker/docker-install#usage)
* [Install Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)

    ```bash
    # There are many ways to install Ansible. pipx is my prefered method.
    python3 -m pip install pipx
    pipx install --include-deps ansible
    ```

    Note: in some environments you may need to use `python` instead of `python3`

# Create Kubenetes nodes

## Copy the example configuration file

```bash
# From the repo's root path
cp group_vars/example-all.yaml group_vars/all.yaml
```

Fill in the `group_vars/all.yaml` with values that are appropriate for your environment.

## Create Kubernetes node VM(s)

By default, a VM is tagged with **kube_node**, **kube_control_plane**, and **etcd**

* **kube_node** : Kubernetes nodes where pods will run.
* **kube_control_plane** : Where Kubernetes control plane components (apiserver, scheduler, controller) will run.
* **etcd**: The etcd server. You should have 3 servers for failover purpose.

For high-availability, it is recommended to have 3+ nodes with the default roles.
See [Kubespray's documentation](https://github.com/kubernetes-sigs/kubespray/blob/v2.27.0/docs/ansible/inventory.md) for more details.

To adjust the role(s) of the VM, adjust the tags:

```bash
# worker, control plane, and etcd node
ansible-playbook create-k8s-vm.yaml -K

# control plane and etcd node
ansible-playbook create-k8s-vm.yaml --extra-vars "vm_tags=kube_control_plane,etcd" -K

# worker node
ansible-playbook create-k8s-vm.yaml --extra-vars "vm_tags=kube_node" -K

# control plane node
ansible-playbook create-k8s-vm.yaml --extra-vars "vm_tags=kube_control_plane" -K

# etcd node
ansible-playbook create-k8s-vm.yaml --extra-vars "vm_tags=etcd" -K
```

# Deploy Kubernetes via Kubespray

## Copy sample inventory files

```bash
DOCKER_IMAGE=quay.io/kubespray/kubespray:v2.27.0

CID=$(docker create "${DOCKER_IMAGE}")
docker cp "${CID}:/kubespray/inventory/sample" mycluster
docker rm "${CID}"
```

Make any desired modifications to the files in "mycluster"

## Run deploy

```bash
docker run --rm --name kubespray --tty --interactive \
    -v "$(pwd)/mycluster:/kubespray/inventory/mycluster" \
    -v "$(pwd)/group_vars/all.yaml:/kubespray/inventory/group_vars/all.yaml" \
    -v "$(pwd)/inventories/proxmox.py:/kubespray/inventory/mycluster/proxmox.py" \
    -v "${HOME}/.ssh:/root/.ssh" \
    "${DOCKER_IMAGE}" bash

# Inside the container, run:
chown $(whoami) ~/.ssh/config
ansible-playbook -i inventory/mycluster/proxmox.py --user=user --become --become-user=root cluster.yml
exit

# Set your SSH config permissions back
sudo chown $(whoami) ~/.ssh/config
sudo chown $(whoami) ~/.ssh/known_hosts
```

# kubectl

Install [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl)

```
The Kubernetes command-line tool, kubectl, allows you to run commands against Kubernetes clusters. You can use kubectl to deploy applications, inspect and manage cluster resources, and view logs.
```

## Authorization

```bash
IP=192.0.1.2  # Controller node IP address
ssh user@${IP} 'mkdir -p "${HOME}/.kube" && sudo cp -f /etc/kubernetes/admin.conf "${HOME}/.kube/config"'

mkdir -p "${HOME}/.kube"
ssh user@${IP} 'sudo cat "${HOME}/.kube/config"' > "${HOME}/.kube/config"
sudo chown $(id -u):$(id -g) "${HOME}/.kube/config"
sed -i "s/127.0.0.1/${IP}/g" "${HOME}/.kube/config"
chmod 400 ~/.kube/config

kubectl get nodes
```
