import bcrypt
from pydantic import BaseModel
class UserInformation:
    def __init__(self, firstName, lastName, email, password,phone,latitude,longitude,image):
        self.firstName=firstName
        self.lastName=lastName
        self.email=email
        self.password=self.password=self._hash_password(password)
        self.phone=phone
        self.latitude=latitude
        self.longitude = longitude
        self.image=image

    def _hash_password(self, password):

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed

class UserInformationCreate(BaseModel):
    firstName : str
    lastName : str
    email : str
    password : str
    phone : str
    latitude:str
    longitude:str
