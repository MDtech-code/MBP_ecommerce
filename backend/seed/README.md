# seed/README.md

## Database Seeder — Pakistan Motorbike Parts Store

### Purpose
Populates the database with sample data for development and testing.

### Files
| File | Purpose |
|------|---------|
| `data.py` | All raw seed data (products, categories, users etc.) |
| `seed_products.py` | Seeds users, categories, brands, bike models, products |
| `seed_cart.py` | Seeds cart items for customer users |
| `seed_all.py` | Master runner — runs everything in correct order |

### Setup Before Running

1. Add placeholder images to `seed/images/`:
    ```
    seed/images/battery.png
    seed/images/brake.png
    seed/images/chain.png
    seed/images/tyre.png
    seed/images/engine.png
    seed/images/light.png
    seed/images/oil.png
    ```
    Any placeholder PNG works — admin will replace via Django admin panel.

2. Ensure your `.env` is configured with correct database credentials.

### Recommended: Test on Dummy DB First

```bash
# 1. Create test database
psql -U postgres -c "CREATE DATABASE motorbike_parts_test;"

# 2. Add test_db to settings.py temporarily
# 3. Run migrations on test db
python manage.py migrate --database=test_db

# 4. Set TARGET_DB = "test_db" in seed_products.py and seed_cart.py

# 5. Run seeder
python seed/seed_all.py

# 6. Verify data, then drop test db
psql -U postgres -c "DROP DATABASE motorbike_parts_test;"