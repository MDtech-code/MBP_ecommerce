# # apps/products/services/category_service.py

# from django.db import transaction
# from django.db.models import ProtectedError
# from apps.products.models import Category

# class CategoryService:
    
#     @staticmethod
#     def safe_delete(category: Category) -> dict:
#         """
#         Safely deletes a category only if it has no subcategories 
#         and no products. Returns a result dict instead of raising 
#         unhandled exceptions.
        
#         Call this from your view/admin instead of category.delete() directly.
#         """
#         subcategory_count = category.subcategories.count()
#         # Add product count check once products app has category FK:
#         # product_count = category.products.count()
        
#         if subcategory_count > 0:
#             return {
#                 'deleted': False,
#                 'reason': f'Category has {subcategory_count} subcategories. '
#                           f'Reassign or delete them first.'
#             }
        
#         try:
#             with transaction.atomic():
#                 category_name = str(category)
#                 category.delete()
#                 return {'deleted': True, 'category': category_name}
#         except ProtectedError as e:
#             return {
#                 'deleted': False, 
#                 'reason': f'Category is referenced by existing records: {e}'
#             }