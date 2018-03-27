#!/bin/bash

if [ $# -lt 2 ]; then unsuccessful_exit "Insufficient parameters supplied. Exiting" 200; fi

USER=$1;
NODEINDEX=$2

echo "Configure node index: $NODEINDEX with user: $USER" >> $CONFIG_LOG_FILE_PATH;

HOMEDIR="/home/$USER";
CONFIG_LOG_FILE_PATH="$HOMEDIR/config.log";
ARTIFACTS_URL_PREFIX="https://raw.githubusercontent.com/hashblock/hashblock-exchange/master/docker/compose";

sudo apt-get -y update
sudo apt-get -y install linux-image-extra-$(uname -r) linux-image-extra-virtual
sudo apt-get -y update

sudo apt-get -y install apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-key fingerprint 0EBFCD88

sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get -y update
sudo apt-get -y install docker-ce
sudo groupadd docker
sudo usermod -aG docker $USER
sudo service docker start

sudo curl -L https://github.com/docker/compose/releases/download/1.18.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

cd $HOMEDIR;
sudo -u $USER /bin/bash -c "wget -N ${ARTIFACTS_URL_PREFIX}/hashblock-node.yaml";

index=0
for node in `seq 0 3`;
do
    if [ $node -eq $NODEINDEX ] 
    then 
        sudo sed -i "s/__NODEINDEX__/$node/" hashblock-node.yaml
    else
        sudo sed -i "s/__PEERINDEX${index}__/$node/" hashblock-node.yaml
        ((index++))
    fi
done 

FAILED_EXITCODE=0;
docker-compose -f hashblock-node.yaml up -d;

FAILED_EXITCODE=$?
if [ $FAILED_EXITCODE -ne 0 ]; then
    echo "FAILED_EXITCODE: $FAILED_EXITCODE " >> $CONFIG_LOG_FILE_PATH;
    exit $FAILED_EXITCODE;
else
    echo "======== Deployment successful! ======== " >> $CONFIG_LOG_FILE_PATH;
    exit 0;
fi

