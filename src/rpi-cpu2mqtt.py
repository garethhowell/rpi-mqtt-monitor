# Python 2 script to check cpu load, cpu temperature and free space,
# on a Raspberry Pi computer and publish the data to a MQTT server.
# RUN pip install paho-mqtt
# RUN sudo apt-get install python-pip

from __future__ import division
import subprocess, time, socket, os
import paho.mqtt.client as paho
import json
import config

# get device host name - used in mqtt topic
hostname = socket.gethostname()


def get_hostname():
                # bash command to get hostname
                full_cmd = "hostname"
                hostname = subprocess.Popen(full_cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
                hostname = hostname.strip('\n')
                #print('local_host = %s', hostname)
                return hostname

def check_used_space(path):
                st = os.statvfs(path)
                free_space = st.f_bavail * st.f_frsize
                total_space = st.f_blocks * st.f_frsize
                used_space = int(100 - ((free_space / total_space) * 100))
                return used_space

def check_cpu_load():
                # bash command to get cpu load from uptime command
                p = subprocess.Popen("uptime", shell=True, stdout=subprocess.PIPE).communicate()[0]
                cores = subprocess.Popen("nproc", shell=True, stdout=subprocess.PIPE).communicate()[0]
                #print('p = %s, cores = %s', p, cores)
                cpu_load = p.split("average:")[1].split(",")[0].replace(' ', '')
                cpu_load = float(cpu_load)/int(cores)*100
                cpu_load = round(float(cpu_load), 1)
                return cpu_load

def check_voltage():
                full_cmd = "vcgencmd measure_volts | cut -f2 -d= | sed 's/000//'"
                voltage = subprocess.Popen(full_cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
                voltage = voltage.strip()[:-1]
                return voltage

def check_swap():
                full_cmd = "free -t | awk 'NR == 3 {print $3/$2*100}'"
                swap = subprocess.Popen(full_cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
                swap = round(float(swap), 1)
                return swap

def check_memory():
                full_cmd = "free -t | awk 'NR == 2 {print $3/$2*100}'"
                memory = subprocess.Popen(full_cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
                memory = round(float(memory), 1)
                return memory

def check_cpu_temp():
                full_cmd = "/opt/vc/bin/vcgencmd measure_temp"
                p = subprocess.Popen(full_cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]
                print(p)
                cpu_temp = p.replace('\n', ' ').replace('\r', '').split("=")[1].split("'")[0]
                return cpu_temp

def check_sys_clock_speed():
                full_cmd = "awk '{printf (\"%0.0f\",$1/1000); }' </sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
                return subprocess.Popen(full_cmd, shell=True, stdout=subprocess.PIPE).communicate()[0]

def register_device(client, name, device_class, entity):
                ''' Send a registration topic to Home Assistant using MQTT
                    :param client: the MQTT client object
                    :param name: How the sensor will be named in HA
                    :param device_class: The HA device_class
                    :param entity: A short form of Namei

                    The MQTT message needs to be sent to a topic of the form "<discovery_prefix>/<component>/[<node_id/]<object_id>/config"
                    The payload needs to be a json representation of:
                        "name": <entity>,
                        "device_class": "sensor",
                        "state_topic": the topic that sensor measurements will sent to
                    '''
                    
                # Construct the configuration topic
                config_topic = config.discovery_prefix + "/sensor/" + local_host + "/" + entity + "/config"
                print("config_topic = %s", config_topic)

                # Construct the "name" element
                json_name = '"name": "' + local_host + "_" + entity + '"'
                print("name = %s", json_name)

                # Construct the state_topic
                json_state_topic = '"state_topic": "' + config.mqtt_topic_prefix + "/" + local_host + "/" + entity + '"'
                print("state_topic = %s", json_state_topic)

                # Construct the device class
                json_device_class = '"device_class": "' + device_class + '"'
                print( 'json_device_class = %s', json_device_class)

                # Construct the unique id
                json_unique_id = '"unique_id": "' + local_host + "_" + entity + '"'
                print("unique_id = %s", json_unique_id)
                
                # Put together the payload
                payload = '{' + json_name + ', ' + json_state_topic + ', ' + json_device_class + ', ' + json_unique_id + '}'
                print("payload = %s", payload)

                # Publish the MQTT config message
                client.publish(config_topic, payload, retain=True)

def register_devices(client, cpu_load, cpu_temp, used_space, voltage, sys_clock_speed, swap, memory):
                if config.cpu_load:
                        register_device(client, "CPU Load", "generic", "cpuload")
                if config.cpu_temp:
                        register_device(client, "CPU Temp", "temperature", "cputemp")
                if config.used_space:
                        register_device(client, "Used Space", "generic", "space")
                if config.voltage:
                        register_device(client, "Voltage", "generic", "volts")
                if config.sys_clock_speed:
                        register_device(client, "Speed", "generic", "speed")
                if config.swap:
                        register_device(client, "Swap Space", "generic", "swap")
                if config.memory:
                        register_device(client, "Memory", "generic", "memory")

def publish_to_mqtt (cpu_load = 0, cpu_temp = 0, used_space = 0, voltage = 0, sys_clock_speed = 0, swap = 0, memory = 0):
                # connect to mqtt server
                client = paho.Client()
                client.username_pw_set(config.mqtt_user, config.mqtt_password)
                client.connect(config.mqtt_host, config.mqtt_port)

                # register the sensors with HA
                register_devices(client, config.cpu_load, config.cpu_temp, config.used_space, config.voltage, \
                        config.sys_clock_speed, config.swap, config.memory)

                # delay the execution of the script
                time.sleep(config.random_delay)

                # publish monitored values to MQTT
                if config.cpu_load:
                        client.publish(config.mqtt_topic_prefix+"/"+hostname+"/cpuload", cpu_load, qos=1)
                        time.sleep(config.sleep_time)
                if config.cpu_temp:
                        client.publish(config.mqtt_topic_prefix+"/"+hostname+"/cputemp", cpu_temp, qos=1)
                        time.sleep(config.sleep_time)
                if config.used_space:
                        client.publish(config.mqtt_topic_prefix+"/"+hostname+"/diskusage", used_space, qos=1)
                        time.sleep(config.sleep_time)
                if config.voltage:
                        client.publish(config.mqtt_topic_prefix+"/"+hostname+"/voltage", voltage, qos=1)
                        time.sleep(config.sleep_time)
                if config.swap:
                        client.publish(config.mqtt_topic_prefix+"/"+hostname+"/swap", swap, qos=1)
                        time.sleep(config.sleep_time)
                if config.memory:
                        client.publish(config.mqtt_topic_prefix+"/"+hostname+"/memory", memory, qos=1)
                        time.sleep(config.sleep_time)
                if config.sys_clock_speed:
                        client.publish(config.mqtt_topic_prefix+"/"+hostname+"/sys_clock_speed", sys_clock_speed, qos=1)
                        time.sleep(config.sleep_time)
                # disconect from mqtt server
                client.disconnect()

def bulk_publish_to_mqtt (cpu_load = 0, cpu_temp = 0, used_space = 0, voltage = 0, sys_clock_speed = 0, swap = 0, memory = 0):
                # compose the CSV message containing the measured values

                values = cpu_load, float(cpu_temp), used_space, float(voltage), int(sys_clock_speed), swap, memory
                values = str(values)[1:-1]

                # connect to mqtt server
                client = paho.Client()
                client.username_pw_set(config.mqtt_user, config.mqtt_password)
                client.connect(config.mqtt_host, config.mqtt_port)

                # publish monitored values to MQTT
                client.publish(config.mqtt_topic_prefix+"/"+hostname, values, qos=1)

                # disconect from mqtt server
                client.disconnect()



if __name__ == '__main__':
                # set all monitored values to False in case they are turned off in the config
                cpu_load = cpu_temp = used_space = voltage = sys_clock_speed = swap = memory = False

                # set default device discovery prefix
                device_discovery_prefix = "homeassistant"
                if config.discovery_prefix:
                        device_discovery_prefix = config.discovery_prefix

                # Get hostname
                local_host = get_hostname()

                # delay the execution of the script
                time.sleep(config.random_delay)

                # collect the monitored values
                if config.cpu_load:
                        cpu_load = check_cpu_load()
                        print("cpu load = ", cpu_load)
                if config.cpu_temp:
                        cpu_temp = check_cpu_temp()
                        print("cpu temp = ", cpu_temp)
                if config.used_space:
                        used_space = check_used_space('/')
                        print("used space = ", used_space)
                if config.voltage:
                        voltage = check_voltage()
                        print("voltage = ", voltage)
                if config.sys_clock_speed:
                        sys_clock_speed = check_sys_clock_speed()
                        print("clock speed = ", sys_clock_speed)
                if config.swap:
                        swap = check_swap()
                        print("swap = ", swap)
                if config.memory:
                        memory = check_memory()
                        print("memory = ", memory)

                # Publish messages to MQTT
                if config.group_messages:
                        bulk_publish_to_mqtt(cpu_load, cpu_temp, used_space, voltage, sys_clock_speed, swap, memory)
                else:
                        publish_to_mqtt(cpu_load, cpu_temp, used_space, voltage, sys_clock_speed, swap, memory)
