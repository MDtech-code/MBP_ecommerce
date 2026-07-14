# # This goes in your CheckoutService later — NOT in the model
# # apps/products/services/inventory_service.py

# @staticmethod
# def create_or_refresh_reservation(
#     product: Product,
#     user: User,
#     quantity: int,
# ) -> StockReservation:
#     """
#     Creates a new reservation or refreshes an existing one.
#     Uses select_for_update to prevent race conditions.
#     """
#     with transaction.atomic():
#         # Lock the product row first
#         product = Product.objects.select_for_update().get(pk=product.pk)
        
#         reservation, created = StockReservation.objects.select_for_update().get_or_create(
#             product=product,
#             user=user,
#             defaults={
#                 "quantity": quantity,
#                 "expires_at": timezone.now() + timedelta(minutes=15),
#             }
#         )
#         if not created:
#             # Refresh existing reservation
#             reservation.quantity = quantity
#             reservation.expires_at = timezone.now() + timedelta(minutes=15)
#             reservation.save(update_fields=["quantity", "expires_at"])
        
#         return reservation