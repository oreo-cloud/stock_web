from pymongo import MongoClient
uri = "mongodb+srv://max0605123789:sx0k4DTRnmO7vnFj@oreo.7trovbo.mongodb.net/?retryWrites=true&w=majority&appName=Oreo"
client = MongoClient(uri, serverSelectionTimeoutMS=5000)
print(client.server_info())
