// data/productDetail.js
import brake from "../assets/images/products/brake.png";

export const productDetail = {
  id: 1,
  name: "Honda CD70 Brake Shoe Set",
  brand: "Honda",
  category: "Brake Parts",
  rating: 4.8,
  reviews: 45,
  price: 850,
  oldPrice: 1000,
  discount: "15%",
  images: [brake, brake, brake, brake],
  stock: true,
  compatibility: ["Honda CD70", "Honda Dream", "Honda Pridor"],
  description:
    "This Honda CD70 Brake Shoe Set is made with high quality friction material for better braking performance and long life. Perfect fit for CD70 and other compatible models.",
  features: [
    "High quality friction material",
    "Perfect fit for Honda CD70",
    "Long lasting and durable",
    "Smooth and safe braking",
  ],
  specifications: [
    { label: "Material", value: "High Quality Fiber" },
    { label: "Brand", value: "Honda" },
    { label: "Category", value: "Brake System" },
    { label: "Weight", value: "500g" },
    { label: "Compatibility", value: "Honda CD70, Dream, Pridor" },
  ],
};

export const relatedProducts = [
  {
    id: 2,
    name: "Brake Pad Set CD70",
    price: 650,
    rating: 4.5,
    reviews: 32,
    image: brake,
  },
  {
    id: 3,
    name: "Chain Sprocket Set",
    price: 2450,
    rating: 4.5,
    reviews: 28,
    image: brake,
  },
  {
    id: 4,
    name: "Front Disc Brake Rotor",
    price: 1870,
    rating: 4.5,
    reviews: 45,
    image: brake,
  },
  {
    id: 5,
    name: "NGK Spark Plug",
    price: 350,
    rating: 4.5,
    reviews: 26,
    image: brake,
  },
];
