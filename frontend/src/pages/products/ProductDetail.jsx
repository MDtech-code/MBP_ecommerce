// pages/product/ProductDetail.jsx
import AccountHeader from "../../components/account/AccountHeader";
import ProductGallery from "../../components/product-detail/ProductGallery";
import ProductInfo from "../../components/product-detail/ProductInfo";
import ProductActions from "../../components/product-detail/ProductActions";
import ProductTrust from "../../components/product-detail/ProductTrust";
import ProductTabs from "../../components/product-detail/ProductTabs";
import RelatedProducts from "../../components/product-detail/RelatedProducts";
import { productDetail, relatedProducts } from "../../data/productDetail";

export default function ProductDetail() {
  return (
    <>
      <AccountHeader />

      <div className="bg-gray-50 min-h-screen">
        <div className="max-w-7xl mx-auto px-6 py-6">

          {/* Breadcrumb */}
          <nav className="text-sm text-gray-500 mb-6 flex items-center gap-2">
            <span className="hover:text-primary cursor-pointer">Home</span>
            <span>›</span>
            <span className="hover:text-primary cursor-pointer">Bike Parts</span>
            <span>›</span>
            <span className="hover:text-primary cursor-pointer">Brake Parts</span>
            <span>›</span>
            <span className="text-gray-800">{productDetail.name}</span>
          </nav>

          {/* Top Section - Gallery + Info */}
          <div className="grid lg:grid-cols-2 gap-8">

            {/* Left - Gallery */}
            <ProductGallery images={productDetail.images} />

            {/* Right - Info */}
            <div>
              <ProductInfo product={productDetail} />
              <ProductActions />
              <ProductTrust />
            </div>

          </div>

          {/* Bottom Section - Tabs + Related */}
          <div className="grid lg:grid-cols-2 gap-8 mt-4">

            {/* Left - Tabs */}
            <div className="bg-white rounded-xl p-6">
              <ProductTabs product={productDetail} />
            </div>

            {/* Right - Related Products */}
            <div className="bg-white rounded-xl p-6">
              <RelatedProducts products={relatedProducts} />
            </div>

          </div>

        </div>
      </div>
    </>
  );
}