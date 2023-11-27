import bcrypt
from pydantic import BaseModel
# class UserLogin:
#     def __init__(self, firstName, lastName, email, password,phone):
#         self.email=email
#         self.password=self.password=self._hash_password(password)
#
#     def _hash_password(self, password):
#         salt = bcrypt.gensalt()
#         hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
#         return hashed

class UserLoginCreate(BaseModel):
    email : str
    password : str
