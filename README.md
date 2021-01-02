# PROXMOX COMMANDS
## Snapshots
```
qm list | grep running | awk '{print $1}' | xargs -I {} qm snapshot {} base --vmstate true
qm list | grep running | awk '{print $1}' | xargs -I {} qm rollback {} base
qm list | awk '{print $1}' | grep [0-9] | xargs -i sh -c "qm start {} || true"
```

# Packer
```

```

# Ansible
## Prepare VMs
```
ansible-playbook proxmox_vm_base.yml
```
# Kubernetes
## Kubespray

### Copy sample inventory files
```
CID=$(docker create quay.io/kubespray/kubespray:v2.14.2)

docker cp ${CID}:/kubespray/inventory/sample mycluster

docker rm ${CID}
```

Make any desired modifications to the files in "mycluster"

### Run deploy
```
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
```
mkdir -p $HOME/.kube

ssh vagrant@10.0.128.252 'mkdir -p $HOME/.kube && sudo cp -f /etc/kubernetes/admin.conf $HOME/.kube/config'

ssh vagrant@10.0.128.252 'sudo cat $HOME/.kube/config' > $HOME/.kube/config

sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### Dashboard Tokens
```
kubectl create serviceaccount dashboard -n default

kubectl create clusterrolebinding dashboard-admin -n default --clusterrole=cluster-admin --serviceaccount=default:dashboard

kubectl get secret $(kubectl get serviceaccount dashboard -o jsonpath="{.secrets[0].name}") -o jsonpath="{.data.token}" | base64 --decode
```

### Dummy deploy
```
kubectl run kubia --image=luksa/kubia --port=8080

kubectl expose pod kubia --type=LoadBalancer --name kubia-http

kubectl get services

kubectl proxy
```