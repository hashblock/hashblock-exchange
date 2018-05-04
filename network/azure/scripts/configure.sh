#!/bin/bash

if [ $# -lt 10 ]; then unsuccessful_exit "Insufficient parameters supplied. Exiting" 200; fi

USER=$1;
NODEINDEX=$2
DNS=$3
PRIVKEY=$4
PUBKEY=$5
NETWORKPRIVKEY=$6
NETWORKPUBKEY=$7
ENIGMAPRIVKEY=$8
ENIGMAPUBKEY=$9
FERNETKEY=$9

TMP_HOME="/sawtooth"

echo "Configure node index: $NODEINDEX with user: $USER" >> $CONFIG_LOG_FILE_PATH;

if [[ -z "${SAWTOOTH_HOME}" ]]; then
  sudo echo "Adding SAWTOOTH_HOME to /etc/environment file" >> $CONFIG_LOG_FILE_PATH;
  sudo echo "SAWTOOTH_HOME=$TMP_HOME" >> /etc/environment;
fi

export SAWTOOTH_HOME=$TMP_HOME

HOMEDIR="/home/$USER";
SAWTOOTH_DATA="$SAWTOOTH_HOME/data"
CONFIG_LOG_FILE_PATH="$HOMEDIR/config.log";
ARTIFACTS_URL_PREFIX="https://raw.githubusercontent.com/hashblock/hashblock-exchange/master/docker/compose";
GENESIS_BATCH="https://raw.githubusercontent.com/hashblock/hashblock-exchange/master/network/azure/config/genesis.batch"

sudo apt-get -y update
sudo apt-get -y install linux-image-extra-$(uname -r) linux-image-extra-virtual

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

sudo mkdir -p "$SAWTOOTH_HOME/keys"
sudo mkdir -p "$SAWTOOTH_HOME/logs"
sudo mkdir -p "$SAWTOOTH_HOME/etc"
sudo mkdir -p $SAWTOOTH_DATA;

if [ ! -e "/sawtooth/keys/validator.priv" ]; then
  sudo echo "Adding /sawtooth/keys/validator.priv key" >> $CONFIG_LOG_FILE_PATH;
  sudo echo $PRIVKEY >> /sawtooth/keys/validator.priv;
fi

if [ ! -e "/sawtooth/keys/validator.pub" ]; then
  sudo echo "Adding /sawtooth/keys/validator.pub key" >> $CONFIG_LOG_FILE_PATH;
  sudo echo $PUBKEY >> /sawtooth/keys/validator.pub;
fi

if [ ! -e "/sawtooth/keys/enigma.priv" ]; then
  sudo echo "Adding /sawtooth/keys/enigma.priv key" >> $CONFIG_LOG_FILE_PATH;
  sudo echo $ENIGMAPRIVKEY >> /sawtooth/keys/enigma.priv;
fi

if [ ! -e "/sawtooth/keys/enigma.pub" ]; then
  sudo echo "Adding /sawtooth/keys/enigma.pub key" >> $CONFIG_LOG_FILE_PATH;
  sudo echo $ENIGMAPUBKEY >> /sawtooth/keys/enigma.pub;
fi

if [ ! -e "/sawtooth/keys/fernet.key" ]; then
  sudo echo "Adding /sawtooth/keys/fernet.key key" >> $CONFIG_LOG_FILE_PATH;
  sudo echo $FERNETKEY >> /sawtooth/keys/fernet.key;
fi

if [ ! -e "/sawtooth/etc/validator.toml" ]; then
  sudo echo "Adding networ public and private keys to /sawtooth/etc/validator.toml" >> $CONFIG_LOG_FILE_PATH;
  sudo echo "network_private_key = '$NETWORKPRIVKEY'" >> /sawtooth/etc/validator.toml;
  sudo echo "network_public_key = '$NETWORKPUBKEY'" >> /sawtooth/etc/validator.toml;
fi

if [ $NODEINDEX -eq 0 ] && [ ! -e "$SAWTOOTH_DATA/block-chain-id" ]; then
  sudo echo "Adding genisis batch file to directory: $SAWTOOTH_DATA" >> $CONFIG_LOG_FILE_PATH;
  cd $SAWTOOTH_DATA;
  sudo wget -N $GENESIS_BATCH;
fi

cd $HOMEDIR;
sudo -u $USER /bin/bash -c "wget -N ${ARTIFACTS_URL_PREFIX}/hashblock-node.yaml";

sudo sed -i "s/__DNS/$DNS/g" hashblock-node.yaml;

index=0
for node in `seq 0 2`;
do
    if [ $node -eq $NODEINDEX ]
    then
        sudo sed -i "s/__NODEINDEX__/$node/" hashblock-node.yaml;
    else
        sudo sed -i "s/__PEERINDEX${index}__/$node/" hashblock-node.yaml;
        ((index++))
    fi
done

if [ ! -e ".env" ]; then
  sudo bash -c 'echo "COMPOSE_HTTP_TIMEOUT=400" > .env'
fi

sudo apt-get -y update
sudo apt-get -y dist-upgrade 
sudo apt-get -y autoremove

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

