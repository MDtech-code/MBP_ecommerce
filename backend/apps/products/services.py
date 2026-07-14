# from decimal import Decimal
# from django.db import transaction
# from django.db.models import F
# from django.core.exceptions import ValidationError
# from apps.coupons.models import Coupon
# from apps.products.models import Product
# from apps.orders.models import Order, OrderItem

# def process_checkout_transaction(user, cart, coupon_code=None) -> Order:
#     """
#     The Single Source of Truth for executing a checkout sequence safely.
#     Wrapping this entire function in transaction.atomic() guarantees that if
#     ANY step fails (out of stock, coupon expired), the whole process rolls back.
#     """
#     with transaction.atomic():
#         subtotal = cart.subtotal  # Computed from cart items
#         discount_amount = Decimal("0.00")
#         coupon_instance = None

#         # 1. ATOMIC COUPON VALIDATION & INCREMENT
#         if coupon_code:
#             # We filter and update in ONE step directly in the DB.
#             # This prevents 50 people from using a 1-use coupon at the exact same millisecond.
#             updated_rows = Coupon.objects.filter(
#                 code=coupon_code,
#                 is_active=True,
#                 times_used__lt=F('usage_limit_total')
#             ).update(times_used=F('times_used') + 1)

#             if updated_rows == 0:
#                 raise ValidationError("This coupon is either invalid, expired, or fully claimed.")
            
#             # Fetch the coupon now that we successfully locked it to compute the discount
#             coupon_instance = Coupon.objects.get(code=coupon_code)
#             discount_amount = coupon_instance.calculate_discount(subtotal)

#         # 2. CONCURRENT STOCK CHECK & ROW LOCKING
#         # Use select_related to prevent N+1 queries when fetching items
#         cart_items = cart.items.select_related('product')
        
#         for item in cart_items:
#             # select_for_update() locks this specific product row in PostgreSQL.
#             # Concurrent checkout requests trying to touch this product will WAIT in line
#             # until this current user's transaction finishes.
#             product = Product.objects.select_for_update().get(pk=item.product.pk)

#             if product.stock < item.quantity:
#                 raise ValidationError(f"Surge traffic alert! {product.name} just ran out of stock.")

#             # Safe to decrement because we have exclusive row access
#             product.stock -= item.quantity
#             product.save(update_fields=['stock'])

#         # 3. CREATE THE ORDER
#         # Calculate shipping and taxes (using your new non-deadlocking models)
#         shipping_fee = Decimal("150.00")  # Example PKR flat rate
#         tax_amount = Decimal("0.00")     # Calculate based on your updated TaxRate ForeignKey

#         order = Order.objects.create(
#             user=user,
#             subtotal=subtotal,
#             discount_amount=discount_amount,
#             shipping_fee=shipping_fee,
#             tax_amount=tax_amount,
#             total_price=(subtotal - discount_amount + shipping_fee + tax_amount),
#             status='PENDING'
#         )

#         # 4. SNAPSHOT ITEMS TO ORDERITEMS
#         for item in cart_items:
#             OrderItem.objects.create(
#                 order=order,
#                 product=item.product,
#                 quantity=item.quantity,
#                 price_at_purchase=item.product.price
#             )

#         # 5. CLEAR THE CART
#         cart.items.all().delete()

#         return order