from jarbas_hive_mind.database import ClientDatabase

name = "JarbasChatRoomTerminal"
access_key = "RESISTENCEisFUTILE"
crypto_key = "resistanceISfutile"
mail = "chatroom@hivemind.com"


with ClientDatabase() as db:
    db.add_client(name, mail, access_key, crypto_key=crypto_key)
