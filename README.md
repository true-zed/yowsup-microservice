# yowsup-microservice
This Project provides a microservice which implements an interface to yowsup2. You can Send/Receive Whatsapp-Messages with any language of your choice.

###Prerequisites:

Install & Configure the yowsup2 CLI Demo.

Use yowsup-cli to register a Number.



###Installation(General):

1. Install rabbitmq
2. Install Flask,Nameko,Flasgger
3. Install yowsup2

###Installation(on Ubuntu):

```bash
# Install Python Stuff:
sudo apt-get install python3-pip python3-dev
pip3 install nameko
pip3 install flask
pip3 install flasgger
pip3 install git+https://github.com/tgalal/yowsup@master
# Install RabbitMQ
apt-get install rabbitmq-server

```


###Configuration:

rename "service.yml.sample to "service.yml" and put your credentials into it.

###Usage:

Run the the Service with:
```
startservice.sh
```

Run the the Api with:
```
startapi.sh
```



Go to:
http://127.0.0.1:5000/apidocs/index.html

You will get the Messages from Whatsapp into the Queue "whatsapp-receive".

Put the messages you want to send into the "whatsapp-send" Queue. The Format of the Messages is JSON.



###Example Messages for other Integrations:

Have a look at swagger documentation.

###Debugging

Run
```
nameko shell
n.rpc.yowsup.send(type="simple", body="This is a test Message!", address="49XXXX")
```