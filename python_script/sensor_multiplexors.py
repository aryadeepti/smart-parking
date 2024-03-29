import time
import json
import board
import adafruit_vcnl4010
import adafruit_tca9548a
import paho.mqtt.client as mqtt
import sys 

# Commandline argument (parking_space id) section.........

if len(sys.argv) <=1:
    print("Please provide a parking space id as the first argument when running this script. \nExample: 'Scriptname.py, ID'")
    exit()

if len(sys.argv) >2:
    print("Too many arguments provided, use just one argument. \nExample: 'Scriptname.py, ID'")
    exit()

else:
    print("Script name: ", sys.argv[0])
    for i in range(1, len(sys.argv)):                                       # Parses argv string from sys.argv[1] 
        print('Argument:', i, 'value:', sys.argv[i])
        id = sys.argv[i]                                                    # Assigns the last argument found to id (but we make sure we only get two arguments so the index i is fixed as "1" in practice)
                                                                            

id=sys.argv[1]                                                              # sys.argv[0] contains filename, sys.argv[1] is the id passed along
print("Parking Space: ", id)                                              # Sets the variable id to the first argument passed along from the commandline  to the script (e.g "Sensorjb 'arg'" )

# init section.........

broker = "test.mosquitto.org"                                              # Test Broker.  # Broker test.mosquitto.org, used when publishing sensory data
topic = "parking_space/"+str(id)                                                 
print("topic: ", topic)
i2c = board.I2C()                                                           # Init board


# Multiplexer section..........
sensorlist=list()
channellist=list()                                                          

tca = adafruit_tca9548a.TCA9548A(i2c)                                       # Init multiplexer

for channel in range(8):                                                    # Scan the multiplexer for sensors with addresses. 
    if tca[channel].try_lock():                                             # Channels are numbered 0-7
        print("Channel {}:".format(channel), end="")
        addresses = tca[channel].scan()
        print([hex(address) for address in addresses if address != 0x70])
        for address in addresses:                                           # Selects all detected values (except 112/0x70 which is the multiplexer address)
            if address !=0x70:
                sensorlist.append(address)                                  # if address is not multiplexer addrees, append to list containing sensor addresses
                channellist.append(channel)                                 # if address is not multiplexer addrees, append to list containing channel numbers
                #print(channellist)
        #print(sensorlist)
        tca[channel].unlock()

total_Slots= len(sensorlist)
print("\nTotal no. of detected seats/sensors: ", total_Slots, "\n")

# Sensor section..........

def get_proximity(sensor):                                                  
	proximity = sensor.proximity
	print('Proximity: {0}'.format(proximity))
	return proximity


# MQTT section (from lab).......

def on_connect(client, userdata, flags, rc):
	if rc==0:
		print("Connection established. Code: "+str(rc))
	else:
		print("Connection failed. Code: " + str(rc))
		
def on_publish(client, userdata, mid):
    print("Published: " + str(mid))
	
def on_disconnect(client, userdata, rc):
	if rc != 0:
		print ("Unexpected disonnection. Code: ", str(rc))
	else:
		print("Disconnected. Code: " + str(rc))
	
def on_log(client, userdata, level, buf):		                            # Message is in buf
    print("MQTT Log: " + str(buf))

# Connect functions for MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish
client.on_log = on_log

# Connect to MQTT 
print("Attempting to connect to broker " + broker)
client.connect(broker)	                                                    # Broker address, port and keepalive (maximum period in seconds allowed between communications with the broker)
client.loop_start()

########### Data processing and publishing ############# 
while True: 
    sensordata_list = list()
    slot_occupied_id = list()
    slot_vaccant_id = list()
    for i in range(len(channellist)):
        number=channellist[i]                                     
        #print("NUMBER: ", number)
        sensor_prox = adafruit_vcnl4010.VCNL4010(tca[number])                
        prox_val = get_proximity(sensor_prox)                               
        if prox_val <=2900:                                   
            sensordata_list.append(False)                                   # Populates a list with i elements (index 0 is for first sensor and index 1 is for second sensor and so on) 
            slot_vaccant_id.append(i+1)
       
        else: 
            sensordata_list.append(True)                                    # Could use values instead of bools and loop over them with a treshhold value to calculate occupiedSeats 
            slot_occupied_id.append(i+1)
   
    occupied_slots = sensordata_list.count(True)
    available_Slots = total_Slots - occupied_slots
    
    parking_status = {                                                     # Create a dict to contain values
        "id": id,                                           
        "occupiedSlots": occupied_slots, 
        "occupiedSlotsId": slot_occupied_id,    
        "availableSlots": available_Slots,
        "availableSlotsId": slot_vaccant_id,
        "totalSlots": total_Slots
    }
    parking_json = json.dumps(parking_status)                             # Convert dict to json string
    payload=parking_json
    client.publish(topic, str(payload), qos=0)                              # Publish
    print(payload)
    time.sleep(1.0)
    

    # What this script is aimed to do:
    #
    # takes the carriageID as an argument from the operator at startup.
    # scans multiplexer for sensors via channels and addresses. 
    # loops dynamically over detected channels to collect data
    # processes data into actionable information and convert to json payload
    # publishes information with a broker under topic parking_space/id.
    # 
    # Be open ended, scalable and adaptable