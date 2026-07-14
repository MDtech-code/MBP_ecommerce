# from django.db import transaction
# from apps.accounts.models import User, UserProfile
# from apps.cart.models import Cart

# def register_new_customer(email, full_name, password) -> User:
#     """
#     Guarantees that a User, their Profile, and their Shopping Cart 
#     are created together. If any step fails, nothing is committed to the database.
#     """
#     # Using transaction.atomic ensures ALL or NOTHING database execution
#     with transaction.atomic():
#         # 1. Create the base authenticated user
#         user = User.objects.create_user(
#             email=email,
#             full_name=full_name,
#             password=password
#         )

#         # 2. Create their profile record (will fail the transaction if it errors out)
#         UserProfile.objects.create(user=user)

#         # 3. Create their persistent shopping cart
#         Cart.objects.create(user=user)

#         return user