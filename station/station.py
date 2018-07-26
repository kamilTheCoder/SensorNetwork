import RPi.GPIO as GPIO
import sensor.sensor as sensors
import socket
import json
import mysql.connector
import datetime
import time

class Station:
    __dbUser = "station"
    __dbPass = "password"
    __dbHost = "localhost"
    __dbName = "readings"
    __dbTableName = "data"

    dht11 = None

    def __init__(self):
        self.ip = "127.0.0.1"
        self.port = 1984
        self.bufferSize = 1024

        self.ip, self.port, self.bufferSize, sensorList = self.__loadConfig()
        self.sensors = self.__initSensors(sensorList)        
        self.__initGpio()


    def registerReading(self):
        time, temp, hum = self.tryRead()

        db = mysql.connector.connect(
            host=self.__dbHost,
            user=self.__dbUser,
            passwd=self.__dbPass,
            database=self.__dbName
            )
        cursor = db.cursor()

        #CREATE TABLE data (tdate DATE, ttime TIME, sensor TEXT, temp NUMERIC, humidity NUMERIC)

        query = "INSERT INTO data (tdate DATE, ttime TIME, sensor TEXT, temp NUMERIC, humidity NUMERIC) VALUES (%s, %s, %s, %s, %s)"
        val = (
            "{}-{}-{}".format(time.year, time.month, time.day),
            "{}:{}:{}".format(time.hour, time.minute, time.second),
            "main",
            temp,
            hum
        )

        cursor.execute(query, val)
        db.commit()
        print("Reading inserted at ID:", cursor.lastrowid)



    def __loadConfig(self):
        print("Loading configuration...")
        with open('config.json', 'r') as f:
            config = json.load(f)

        ip = config['station']['ip']
        port = config['station']['port']
        buffSize = config['station']['buffSize']

        sensors = []
        for sensor in config['sensors']:
            name = sensor['name']
            pin = sensor['pin']
            sensors.append((name, pin))

        return ip, port, buffSize, sensors


    def printConfig(self):
        print("configuration:")
        print("\tip:\t\t{}".format(self.ip))
        print("\tport:\t\t{}".format(self.port))
        print("\tbuffSize:\t{}".format(self.bufferSize))
        print("sensors:")
        for s in self.sensors:
            print("\tname: {}\tpin: {}".format(s.name, s.gpio))


    def __initGpio(self):
        print("Initialising GPIO...")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup()


    def __initSensors(self, sensorList): 
        print("Initialising sensor list")
        result = []
        for sensorConf in sensorList:
            if sensorConf[0] == 'DHT11': 
                print("\tFound DHT11 at pin {}".format(sensorConf[1]))
                result.append(sensors.Dht11Sensor(sensorConf[1]))
            else:
                print("\WARNING: Unknown sensor {}".format( sensorConf[0]))

        return result


    def readSensor(self,i):
        if len(self.sensors) < i+1:
            print("WARNING: Trying to access sensor #{}, which does not exist".format(i))
            return None

        return self.sensors[i].read()


    def readAllSensors(self):
        reads = []
        for s in self.sensors:
            reads.append(s.read())

        return reads


    def readDht11(self):
        for s in self.sensors:
            if isinstance(s, sensors.Dht11Sensor):
                return s.read()
    

    def tryRead(self):
        retries = 0
        maxRetries = 10
        result = None
        now = None
        print("Attempting to read...")
        while retries < maxRetries:        
            result = self.readDht11()
            now = datetime.datetime.now()

            if result == None or not result.is_valid():
                retries += 1
                continue
    
            print("Data read @ " + str(now))
            print("\tTemperature: %d C" % result.temperature)
            print("\tHumidity: %d %%" % result.humidity)

        if retries == maxRetries:
            print("Finished reading after {} failed retries".format(retries))
            return now, None, None

        return now, result.temperature, result.humidity

