# PROXMOX KUBERNETES BOOTSTRAP

## Description
This is a collection of resources to get a Kubernetes cluster up and running in a Proxmox Virtual Environment. These tools and commands assume the user is executing in a Linux or Linux-like environment.
# Prerequisites
* Proxmox server up and running
* A set of RSA SSH keys generated
* Install Python 3
* [Install Docker](https://github.com/docker/docker-install#usage)
* [Install Packer 1.6.6+](https://learn.hashicorp.com/tutorials/packer/getting-started-install)
* Install Ansible and its dependencies

    ```bash
    pip install -r ansible/requirements.txt
    ```
    Note: in some environments you may need to use `pip3` instead of `pip`
* Install Ansible collections
    ```bash
    ansible-galaxy install -r ansible/requirements.yml
    ```

# Packer
Copy the template variables file
```bash
cp packer/example-variables.json packer/variables.json
```
Fill in the `packer/variables.json` file with values that are appropriate for your environment.

Now, create your ubuntu-2004-server template
```bash
cd packer  # Note: packer's 'http_directory' is a relative path
packer build -var-file="variables.json" ubuntu-2004-server.json
```
Expect the installation to take a little over 10 minutes. This time may vary depending on your hardware specs and network performance.

Note: Packer may fail if the VM doesn't have access to the same network as your local machine. (e.g. WSL on Windows or a non-flat network environment)

Workaround for WSL: Install Packer on Windows and run these commands from PowerShell or CMD

# Ansible
**Note: All 'ansible-playbook' commands should be run from the 'ansible' directory**
## Create Kubernetes master VMs
```bash
ansible-playbook proxmox_k8s_new_master_vm.yml

# Use a for loop to create multiple systems. Replace the 'X' with the number of VMs you want.
for i in {1..X} ; do proxmox_k8s_new_master_vm.yml ; done
```
## Create Kubernetes kubelet VMs
```bash
ansible-playbook proxmox_k8s_new_kubelet_vm.yml

# Use a for loop to create multiple systems. Replace the 'X' with the number of VMs you want.
for i in {1..X} ; do proxmox_k8s_new_kubelet_vm.yml ; done
```

## Prepare VMs
```bash
ansible-playbook proxmox_k8s_vm_base_setup.yml
```
# Kubernetes
## Kubespray

### Copy sample inventory files
```bash
CID=$(docker create quay.io/kubespray/kubespray:v2.14.2)

docker cp ${CID}:/kubespray/inventory/sample mycluster

docker rm ${CID}
```

Make any desired modifications to the files in "mycluster"

### Run deploy
```bash
docker run --name kubespray -d -t \
    -v $(pwd)/mycluster:/kubespray/inventory/mycluster \
    -v $(pwd)/ansible/inventories/proxmox.json:/kubespray/inventory/mycluster/proxmox.json \
    -v $(pwd)/ansible/inventories/proxmox.py:/kubespray/inventory/mycluster/proxmox.py \
    -v $HOME/.ssh/id_rsa:/root/.ssh/id_rsa \
    quay.io/kubespray/kubespray:v2.14.2

docker exec -it kubespray ansible-playbook -i inventory/mycluster/proxmox.py -i inventory/mycluster/inventory.ini  --user=vagrant --become --become-user=root cluster.yml
```
## kubectl
### Authorization
```bash
mkdir -p $HOME/.kube

ssh vagrant@10.0.128.252 'mkdir -p $HOME/.kube && sudo cp -f /etc/kubernetes/admin.conf $HOME/.kube/config'

ssh vagrant@10.0.128.252 'sudo cat $HOME/.kube/config' > $HOME/.kube/config

sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### Dashboard Tokens
```bash
kubectl create serviceaccount dashboard -n default

kubectl create clusterrolebinding dashboard-admin -n default --clusterrole=cluster-admin --serviceaccount=default:dashboard

kubectl get secret $(kubectl get serviceaccount dashboard -o jsonpath="{.secrets[0].name}") -o jsonpath="{.data.token}" | base64 --decode
```

### Dummy deploy
```bash
kubectl run kubia --image=luksa/kubia --port=8080

kubectl expose pod kubia --type=LoadBalancer --name kubia-http

kubectl get services

kubectl proxy
```
# Etc. - Proxmox CLI cheat sheet
Note: These commands must be run on the Proxmox host as root
## Snapshot commands
```bash
qm list | grep running | awk '{print $1}' | xargs -I {} qm snapshot {} base --vmstate true
qm list | grep running | awk '{print $1}' | xargs -I {} qm rollback {} base
qm list | awk '{print $1}' | grep [0-9] | xargs -i sh -c "qm start {} || true"
```