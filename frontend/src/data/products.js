import brake from "../assets/images/products/brake.png";
import chain from "../assets/images/products/chain.png";
import battery from "../assets/images/products/battery.png";
import tyre from "../assets/images/products/tyre.png";



export const products = [
  {
    id: 1,
    name: "Honda CD70 Brake Shoe Set",
    bike: "Honda CD70",
    rating: 4.8,
    reviews: 45,
    price: 850,
    oldPrice: 1000,
    discount: "15%",
    image: brake,
  },

  {
    id: 2,
    name: "Yamaha YBR Chain Set",
    bike: "Yamaha YBR",
    rating: 4.7,
    reviews: 38,
    price: 2450,
    oldPrice: 2800,
    discount: "10%",
    image: chain,
  },

  {
    id: 3,
    name: "Delkor Bike Battery 12V",
    bike: "Universal",
    rating: 4.9,
    reviews: 33,
    price: 2850,
    oldPrice: 3200,
    discount: "12%",
    image: battery,
  },

  {
    id: 4,
    name: "Tubeless Bike Tyre",
    bike: "Honda 125",
    rating: 4.6,
    reviews: 29,
    price: 4200,
    oldPrice: 4800,
    discount: "10%",
    image: tyre,
  },

  ...Array.from({ length: 8 }, (_, i) => ({
    id: i + 10,

    name: "Premium Bike Part",

    bike: "Honda / Yamaha",

    rating: 4.7,

    reviews: 20,

    price: 1500,

    oldPrice: 1800,

    discount: "15%",

    image: brake,
  })),
];