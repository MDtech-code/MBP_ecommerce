// components/common/Footer.jsx
import { FaFacebookF, FaInstagram, FaYoutube, FaTiktok } from "react-icons/fa";
import { SiVisa, SiMastercard } from "react-icons/si";
import footer_logo from "../../assets/images/logo/auth_banner_logo.png";

export default function Footer() {
  return (
    <footer className="bg-black text-white mt-20">

      {/* Main Footer */}
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="flex divide-x divide-gray-700">

          {/* Col 1 - Brand */}
          <div className="pr-10 w-72 shrink-0">

            {/* Logo */}
            {/* Logo */}
<div className="flex items-center gap-3">
  <img
    src={footer_logo}
    alt="BikeExpress"
    className="h-12 object-contain"
  />
  <div>
    <p className="font-black text-lg leading-none tracking-wide text-white">
      BIKEEXPRESS
    </p>
    <p className="text-gray-400 text-xs tracking-widest mt-1">
      QUALITY PARTS, SMOOTH RIDES
    </p>
  </div>
</div>

            {/* Description */}
            <p className="text-gray-400 text-sm leading-relaxed mt-4">
              Your trusted source for genuine motorcycle parts and accessories in Pakistan.
            </p>

            {/* Social Icons */}
            <div className="flex items-center gap-3 mt-6">
              <a
                href="#"
                className="w-8 h-8 rounded-full border border-gray-600 flex items-center justify-center text-gray-400 hover:border-white hover:text-white transition"
              >
                <FaFacebookF size={13} />
              </a>
              <a
                href="#"
                className="w-8 h-8 rounded-full border border-gray-600 flex items-center justify-center text-gray-400 hover:border-white hover:text-white transition"
              >
                <FaInstagram size={13} />
              </a>
              <a
                href="#"
                className="w-8 h-8 rounded-full border border-gray-600 flex items-center justify-center text-gray-400 hover:border-white hover:text-white transition"
              >
                <FaYoutube size={13} />
              </a>
              <a
                href="#"
                className="w-8 h-8 rounded-full border border-gray-600 flex items-center justify-center text-gray-400 hover:border-white hover:text-white transition"
              >
                <FaTiktok size={13} />
              </a>
            </div>

          </div>

          {/* Col 2 - Customer Service */}
          <div className="px-10">
            <h3 className="font-bold text-sm uppercase tracking-wider mb-5">
              Customer Service
            </h3>
            <ul className="space-y-3">
              {[
                "Contact Us",
                "Track Order",
                "Returns & Refunds",
                "Shipping Policy",
                "FAQ",
              ].map((item) => (
                <li key={item}>
                  <a
                    href="#"
                    className="text-gray-400 text-sm hover:text-white transition"
                  >
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Col 3 - My Account */}
          <div className="px-10">
            <h3 className="font-bold text-sm uppercase tracking-wider mb-5">
              My Account
            </h3>
            <ul className="space-y-3">
              {[
                "My Profile",
                "Order History",
                "Wishlist",
                "Addresses",
                "Logout",
              ].map((item) => (
                <li key={item}>
                  <a
                    href="#"
                    className="text-gray-400 text-sm hover:text-white transition"
                  >
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Col 4 - Information */}
          <div className="px-10">
            <h3 className="font-bold text-sm uppercase tracking-wider mb-5">
              Information
            </h3>
            <ul className="space-y-3">
              {[
                "About Us",
                "Terms & Conditions",
                "Privacy Policy",
                "Terms of Use",
              ].map((item) => (
                <li key={item}>
                  <a
                    href="#"
                    className="text-gray-400 text-sm hover:text-white transition"
                  >
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Col 5 - Newsletter */}
          <div className="pl-10 flex-1">
            <h3 className="font-bold text-sm uppercase tracking-wider mb-5">
              Newsletter
            </h3>
            <p className="text-gray-400 text-sm leading-relaxed mb-5">
              Subscribe to get updates on new products and exclusive offers.
            </p>
            <div className="flex">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 bg-white text-gray-800 text-sm px-4 py-2.5 rounded-l-lg outline-none placeholder-gray-400 min-w-0"
              />
              <button className="bg-primary text-white text-xs font-black px-5 py-2.5 rounded-r-lg hover:bg-red-700 transition whitespace-nowrap">
                SUBSCRIBE
              </button>
            </div>
          </div>

        </div>
      </div>

      {/* Bottom Bar */}
      <div className="border-t border-gray-700">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">

          {/* Copyright */}
          <p className="text-gray-500 text-xs">
            © 2024 BikeExpress. All Rights Reserved.
          </p>

          {/* Payment Methods */}
          <div className="flex items-center gap-5">

            {/* VISA */}
            <SiVisa size={38} className="text-white" />

            {/* Mastercard */}
            <SiMastercard size={30} className="text-yellow-400" />

            {/* Easypaisa */}
            <span className="font-bold text-sm tracking-wide">
              <span className="text-green-400">o</span>
              <span className="text-white">asypaisa</span>
            </span>

            {/* JazzCash */}
            <span className="font-bold text-sm">
              <span className="text-red-400 italic">Jazz</span>
              <span className="text-white">Cash</span>
            </span>

          </div>

        </div>
      </div>

    </footer>
  );
}