# # yourapp/backends.py

# from django.contrib.auth.backends import ModelBackend
# from django.contrib.auth import get_user_model

# import logging
# logger = logging.getLogger(__name__)

# class MatriculaBackend(ModelBackend):
#     def authenticate(self, request, matricula=None, password=None, **kwargs):
#         logger.debug(f"Custom backend called with matricula: {matricula}")

#         UserModel = get_user_model()
#         try:
#             user = UserModel.objects.get(matricula=matricula)
#             logger.debug(f"User found: {user}")
#             if user.check_password(password):
#                 logger.debug("Password is correct")
#                 if self.user_can_authenticate(user):
#                     logger.debug("User can authenticate")
#                     return user
#                 else:
#                     logger.debug("User cannot authenticate")
#             else:
#                 logger.debug("Incorrect password")
#         except UserModel.DoesNotExist:
#             logger.debug("User does not exist")
#         return None
