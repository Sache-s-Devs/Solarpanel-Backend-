# main.py

from math import pi, sqrt
import math
import json
import pyproj
from PIL import Image, ImageDraw
from bson.objectid import ObjectId
import base64
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, HTTPException, Response,Header,Request
import jwt
from fastapi import HTTPException, Depends
from cachetools import LRUCache
import requests
import rasterio
from io import BytesIO

from UserLogin import UserLoginCreate
from UserInformation import UserInformation,UserInformationCreate
import bcrypt
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# import UserInformation
uri = "mongodb+srv://aukikaurnab:punar123@cluster0.1wvxghl.mongodb.net/?retryWrites=true&w=majority"
jwt_key="CI6MTY5NzI3Njg0MSwiaWF0IjoxNjk3Mjc2ODQxfQ.#%G@3F(#E>#FE3r2f33f[CV3f{#;3[;f3f3Rr[12d35"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

app = FastAPI()
image_height=0
image_width=0
area=0
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cache = LRUCache(maxsize=1000)

def verify_token(request: Request):
    authorization_header = request.headers.get("Authorization")
    # print(authorization_header)
    if authorization_header is None or not authorization_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    token = authorization_header.split(" ")[1]

    try:
        decoded_token = jwt.decode(token, jwt_key, algorithms=['HS256'])
        return decoded_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Invalid token")
def compare_password(plaintext_password, hashed_password):
    return bcrypt.checkpw(plaintext_password.encode('utf-8'), hashed_password)
def convert_tif_to_png(response):
    # try:
        # Fetch the TIF image from the URL
        # response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful

        # Open and convert TIF to PNG
        tif_buffer = BytesIO(response.content)
        tif_image = Image.open(tif_buffer)
        png_buffer = BytesIO()
        tif_image.save(png_buffer, format="PNG")
        png_buffer.seek(0)

        # Base64 encode the PNG image
        png_base64 = base64.b64encode(png_buffer.getvalue()).decode('utf-8')

        # Generate HTML with the base64-encoded image
        html_content = f'data:image/png;base64,{png_base64}'

        # return HTMLResponse(content=html_content)


        headers = {
            "Access-Control-Allow-Origin": "*"
        }
        # print(get_image_dimensions_from_base64(html_content))
        return html_content

def latlon_to_pixel(image, x, y):
    try:
        # Download the image from the URL
        response = image

        if response.status_code == 200:
            image_data = BytesIO(response.content)

            # Open the image using rasterio
            with rasterio.open(image_data) as src:
                # Transform the target coordinates to pixel coordinates
                pixel_coords = src.index(x, y)

                # Get the image dimensions
                max_width = src.width
                max_height = src.height
                global image_height
                global image_width
                image_height = src.width
                image_width = src.height

                # Check if the calculated coordinates are within the image bounds
                if 0 <= pixel_coords[0] < max_width and 0 <= pixel_coords[1] < max_height:
                    return pixel_coords[0], pixel_coords[1]
                else:
                    return None  # Coordinates are outside the image bounds
        else:
            print("Failed to download the image")
            return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

def convert_coordinates(from_epsg, to_epsg, x, y):
    try:
        transformer = pyproj.Transformer.from_crs(from_epsg, to_epsg, always_xy=True)
        result = transformer.transform(x, y)
        return result
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
def get_buildingInsights(lat,lon):

    building=requests.get(f"https://solar.googleapis.com/v1/buildingInsights:findClosest?location.latitude={lat}&location.longitude={lon}&requiredQuality=HIGH&key=AIzaSyCmexVycGxqBcD2X6_mNGqMVYIgtyglGNM").json()
    return building
def area_to_radius(area: float) -> float:
    return sqrt(area / pi)

# @app.get("/getPixelCoordinate")
def get_pixel_coordinate(latitude: float, longitude:float, image):
    to_epsg = 'epsg:32617'  # Replace with your source EPSG code
    from_epsg = 'epsg:4326'  # Replace with your target EPSG code

    # Specify the coordinates you want to convert

    y, x = latitude,longitude

    # print(f"Initial coordinates (Longitude, Latitude): ({x}, {y})")
    # Call the function to convert coordinates
    result = convert_coordinates(from_epsg, to_epsg, x, y)

    if result is not None:
        lon, lat = result
        # print(f"Converted coordinates (Longitude, Latitude): ({lon}, {lat})")
    else:
        print("An error occurred during coordinate conversion.")


    result = latlon_to_pixel(image, lon, lat)

    if result is not None:
        column, row = result
        # print(f"Pixel coordinates (Column, Row): ({column}, {row})")
        return {"column":column, "row":row}
    else:
        print("The target coordinates are outside the image bounds or an error occurred.")

# @app.get("/getCenteredImage")
def get_image(lat,lon):
    # key = str(lat+lon)
    # print(lat,lon)
    # if key in cache:
    #     return cache[key]
    # replace it with actual buildingInsightsApi
    buildingInsights= get_buildingInsights(lat,lon)
    groundArea=buildingInsights.get("solarPotential").get("wholeRoofStats").get("areaMeters2")

    radius=math.ceil(area_to_radius(groundArea))

    actualLatOfTheBuildingCenter,actualLonOfTheBuildingCenter=buildingInsights.get("center")["latitude"],buildingInsights.get("center")["longitude"]


    getImageURL=f"https://solar.googleapis.com/v1/dataLayers:get?location.latitude={actualLatOfTheBuildingCenter}&location.longitude={actualLonOfTheBuildingCenter}&radiusMeters={radius*2}&view=IMAGERY_LAYERS&requiredQuality=HIGH&pixelSizeMeters=0.1&key=AIzaSyCmexVycGxqBcD2X6_mNGqMVYIgtyglGNM"

    imageRGBURL = requests.get(getImageURL).json().get("rgbUrl")+"&key=AIzaSyCmexVycGxqBcD2X6_mNGqMVYIgtyglGNM"


    roof_segment=[]
    pixel_coordinate = []
    # print()
    image = requests.get(imageRGBURL)
    # print(buildingInsights["solarPotential"]["roofSegmentStats"])
    for roof in buildingInsights["solarPotential"]["roofSegmentStats"]:
        # print(roof)
        center=get_pixel_coordinate(roof.get("center").get("latitude"), roof.get("center").get("longitude"), image)
        sw=get_pixel_coordinate(roof.get("boundingBox").get("sw").get("latitude"), roof.get("boundingBox").get("sw").get("longitude"), image)
        ne=get_pixel_coordinate(roof.get("boundingBox").get("ne").get("latitude"), roof.get("boundingBox").get("ne").get("longitude"), image)
        area=roof.get("stats").get("areaMeters2")


        roof_segment.append({"sw":sw,"ne":ne,"center":center,"area":area})


    for panel in buildingInsights["solarPotential"]["solarPanels"]:
        pixel_coordinate.append({"pixel_coordinate":get_pixel_coordinate(panel["center"]["latitude"],panel["center"]["longitude"],image),"orientation":panel["orientation"],"yearlyEnergyDcKwh":panel["yearlyEnergyDcKwh"],"azimuth":buildingInsights["solarPotential"]["roofSegmentStats"][panel["segmentIndex"]]["azimuthDegrees"],"orientation":panel["orientation"],"segmentIndex":panel["segmentIndex"],"pitch":buildingInsights["solarPotential"]["roofSegmentStats"][panel["segmentIndex"]]["pitchDegrees"]})

    headers = {
        "Access-Control-Allow-Origin": "*"
    }


    tiff_png = convert_tif_to_png(image)
    # cache[key] = JSONResponse(content={"imageURL":tiff_png,"pixel_coordinates":pixel_coordinate},headers=headers)

    # return JSONResponse(content={"imageURL": tiff_png, "pixel_coordinates":pixel_coordinate ,"roof_segment":roof_segment},headers=headers)

    return {"imageURL": tiff_png, "pixel_coordinates":pixel_coordinate ,"roof_segment":roof_segment,"areaWholeRoof":groundArea, "financialAnalysis":buildingInsights["solarPotential"]["financialAnalyses"]}
@app.get("/test")
async def test():
   return JSONResponse(content={"message": "Hello"})

@app.post("/registration/")
async def create_item(user: UserInformationCreate):
    new_item = UserInformation(user.firstName, user.lastName, user.email, user.password, user.phone, user.latitude, user.longitude, get_image(float(user.latitude),float(user.longitude)))
    try:
        # result = client.mydatabase.items.insert_one(new_item.__dict__)
        userInfoByEmail = client.mydatabase.user.find_one({"email": user.email}, {"_id": 0, "password": 0})
        userInfoByPhone= client.mydatabase.user.find_one({"phone": user.phone}, {"_id": 0, "password": 0})

        if userInfoByEmail:
            return {"message":"email address exists. Use different one.","error":True}
        if userInfoByPhone:
            return {"message":"phone number exists. Use different one.","error":True}
        result = client.mydatabase.user.insert_one(new_item.__dict__)
        print(f"Inserted document with ID: {result.inserted_id}")
        # return JSONResponse(content={"id": result.inserted_id})
        token = jwt.encode({"user_id": str(result.inserted_id)}, key=jwt_key, algorithm="HS256")
        return JSONResponse(content={"id": str(result.inserted_id),"token":token,"error":False})
    except Exception as e:
        print(f"Error inserting document: {e}")

@app.post("/login/")
async def create_item(user: UserLoginCreate):
    try:
        userInfo = client.mydatabase.user.find_one({"email": user.email}, {"email": 0})

        if user==None:
            return JSONResponse(content={"message":"invalid credentials","error":True})
        if compare_password(user.password, userInfo["password"]):

            token = jwt.encode({"user_id": str(userInfo["_id"])}, key=jwt_key, algorithm="HS256")

            return JSONResponse(content={ "id":str(userInfo["_id"]),"token": token,"error":False})

        else:
            return JSONResponse(content={"message":"invalid credentials","error":True})


    except Exception as e:
        print(f"Error inserting document: {e}")

@app.get("/userInformation/")
async def get_users(user_id: dict = Depends(verify_token)):
    try:
        user = client.mydatabase.user.find_one({"_id": ObjectId(user_id["user_id"])}, {"_id": 0,"password":0})

        # Step 1: List all possible segment indexes
        # remove_edge_panels(user["image"]["pixel_coordinates"])
        return user
    except Exception as e:
        print(f"Error fetching users: {e}")


# def coordinates_by_segment_index(data):
#     segment_indexes = set(item['segmentIndex'] for item in data)
#
#     # Step 2: Divide the coordinates based on indexes
#     coordinates_by_index = {index: [] for index in segment_indexes}
#
#     for item in data:
#         segment_index = item['segmentIndex']
#         coordinates_by_index[segment_index].append(item['pixel_coordinate'])
#
#     return coordinates_by_index
#
#
# def filter_border_coordinates(segment_data):
#     min_column = min(coord['column'] for coord in segment_data)
#     max_column = max(coord['column'] for coord in segment_data)
#     min_row = min(coord['row'] for coord in segment_data)
#     max_row = max(coord['row'] for coord in segment_data)
#
#     filtered_data = [
#         coord for coord in segment_data
#         if coord['column'] != min_column and coord['column'] != max_column
#            and coord['row'] != min_row and coord['row'] != max_row
#     ]
#
#     return filtered_data
#
#
# def filtered_data_by_segment(data):
#     filtered_data_by_segment = {
#         segment_index: filter_border_coordinates(segment_data)
#         for segment_index, segment_data in coordinates_by_segment_index(data).items()
#     }
#
#     return  filtered_data_by_segment
#

def remove_edge_panels(data):
    # Group panels by segment index
    grouped_data = {}
    for panel in data:
        index = panel['segmentIndex']
        if index not in grouped_data:
            grouped_data[index] = []
        grouped_data[index].append(panel)

    # Identify edge panels for each segment
    panels_to_remove = []
    ## image height and image width are found from global variable

    for panels in grouped_data.values():
        min_row = min(p['pixel_coordinate']['row'] for p in panels)
        max_row = max(p['pixel_coordinate']['row'] for p in panels)
        min_column = min(p['pixel_coordinate']['column'] for p in panels)
        max_column = max(p['pixel_coordinate']['column'] for p in panels)

        for panel in panels:
            row = panel['pixel_coordinate']['row']
            column = panel['pixel_coordinate']['column']
            if row == min_row or row == max_row or column == min_column or column == max_column:
                panels_to_remove.append(panel)

    # Remove the edge panels
    for panel in panels_to_remove:
        data.remove(panel)

    return data











@app.get("/getImage/")
async def read_greet(lat: str,lon: str):
    try:
        key = str(lat + lon)
        print(lat, lon)
        if key in cache:
            return cache[key]

        data=get_image(lat, lon)
        print("area",data["areaWholeRoof"])
        # if data["areaWholeRoof"]>170:
        #     print("panels trimmed")
        #     remove_edge_panels(data["pixel_coordinates"])
        # else:
        #     print("panels not trimmed")

        cache[key] = data


        return data
    except Exception as e:
        print(f"Error fetching users: {e}")


