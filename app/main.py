from http.client import HTTPException
from turtle import pos
from unicodedata import category
from fastapi import FastAPI, status, HTTPException
from typing import Dict, Optional, List
from fastapi.params import Body
from pydantic import BaseModel
import json
import csv
from pymongo import MongoClient
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

class EluNode(BaseModel):
    fullName:str = ""
    positionName:str = ""
    location:str = ""
    terrUid: str = ""
    stillEffective:bool = True

class AdminUnitFlatNode(BaseModel):
  id:int = -1
  name:str = ""
  kind:str = ""
  code: str = ""

# Provide the mongodb atlas url to connect python to mongodb using pymongo
USERNAME = "explain"
PASSWORD = "explain"

try:
    client = MongoClient(f"mongodb+srv://{USERNAME}:{PASSWORD}@explain.jswpjc0.mongodb.net/?retryWrites=true&w=majority")
except:
    raise RuntimeError("Cannot connect to MongoDB serveur")

db = client.test


already_collected = db.list_collection_names()


if "elected" not in already_collected:
    with open("./app/data/elu.json", encoding = 'utf-8') as f:
        f_data = json.load(f)
    if isinstance(f_data, list):
        print("we inserted many records")
        db["elected"].insert_many(f_data) 
    else:
        print("we inserted one records")
        db["elected"].insert_one(f_data)

fields = ["code", "name", "kind"]

if "territoires" not in already_collected:
    with open("./app/data/territories.csv", encoding = 'utf-8') as f:
        reader = csv.DictReader(f)
        for each in reader:
            row = {}
            row['_id'] = each['id']
            for field in fields:
                row[field] = each[field]
            db["territoires"].insert_one(row)


collection_elected = db["elected"]

collection_territoires = db["territoires"]
origins = [
    "http://localhost:4200",
]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

http_cache = {}

#cursor = collection_elected.find({"_source.positions":{"$elemMatch": {"territory_uid" : {"$eq": "FRCOMM03258"}}}} , {"_source.fullname":1, "_source.positions":1})


# async keyword: complex tasks like sending multiplex messages to API/ DataBases
@app.get("/elected/{code}")
async def get_elected_by_admin_code(code: str) -> List[Optional[EluNode]]:
    if len(code) < 1 or type(code) != str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Please provide a valide territory code")

    if code in http_cache:
        return http_cache[code]


    cursor = collection_elected.find({"_source.positions":{"$elemMatch": {"territory_uid" : {"$eq": code}}}} , {"_source.fullname":1, "_source.positions":1})

    ans = []
    for doc in cursor:
        for pos in doc['_source']['positions']:
            temp = EluNode()
            if pos['end_date']==None:
                temp.stillEffective = True
            else:
                temp.stillEffective = False
            temp.fullName = doc['_source']['fullname']
            temp.positionName = pos['role_uid']
            locations = collection_territoires.find_one({"code":{"$eq":code[6:]}}, {"name":1})
            temp.location = locations["name"]
            temp.terrUid = code
            ans.append(temp)

    http_cache[code] = ans

    return ans

http_cache2 = {}

@app.get("/territoires/{name}")
async def get_territories_by_name(name: str) -> List[Optional[EluNode]]:
    if len(name) < 1 or type(name) != str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Please provide a valide territory code")

    if name in http_cache2:
        return http_cache2[name]

    body = ".*" + name + "*."

    cursor = collection_territoires.find({"name":{"$regex":body, '$options' : 'i'}})
    ans = []
    for doc in cursor:
        print("result!: ", doc)
        temp = AdminUnitFlatNode()
        temp.id = int(doc['_id'])
        temp.code = doc["code"]
        temp.name = doc["name"]
        temp.kind = doc["kind"]
        ans.append(temp)

    http_cache[name] = ans

    return ans

#client.close()

@app.get("/")
async def main():
    return {"message": "Hello World"}