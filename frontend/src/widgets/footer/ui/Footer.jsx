// src/components/layout/Footer.jsx
import { FaFacebookF, FaInstagram, FaYoutube, FaTiktok } from "react-icons/fa";
import { SiVisa, SiMastercard } from "react-icons/si";
import footer_logo from "@shared/assets/images/logo/auth_banner_logo.png"

export default function Footer() {
  return (
    <footer className="bg-black text-white mt-20">

      {/* Main Footer */}
      <div className="max-w-7xl mx-auto px-6 py-12">
        {/* Changed from strict flex to a responsive grid that becomes flex on lg screens */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:flex lg:divide-x lg:divide-gray-700 gap-10 lg:gap-0">

          {/* Col 1 - Brand */}
          <div className="lg:pr-10 lg:w-72 shrink-0">
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

            <p className="text-gray-400 text-sm leading-relaxed mt-4">
              Your trusted source for genuine motorcycle parts and accessories in Pakistan.
            </p>

            <div className="flex items-center gap-3 mt-6">
              <a href="#" className="w-8 h-8 rounded-full border border-gray-600 flex items-center justify-center text-gray-400 hover:border-white hover:text-white transition">
                <FaFacebookF size={13} />
              </a>
              <a href="#" className="w-8 h-8 rounded-full border border-gray-600 flex items-center justify-center text-gray-400 hover:border-white hover:text-white transition">
                <FaInstagram size={13} />
              </a>
              <a href="#" className="w-8 h-8 rounded-full border border-gray-600 flex items-center justify-center text-gray-400 hover:border-white hover:text-white transition">
                <FaYoutube size={13} />
              </a>
              <a href="#" className="w-8 h-8 rounded-full border border-gray-600 flex items-center justify-center text-gray-400 hover:border-white hover:text-white transition">
                <FaTiktok size={13} />
              </a>
            </div>
          </div>

          {/* Col 2 - Customer Service */}
          <div className="lg:px-10">
            <h3 className="font-bold text-sm uppercase tracking-wider mb-5">
              Customer Service
            </h3>
            <ul className="space-y-3">
              {["Contact Us", "Track Order", "Returns & Refunds", "Shipping Policy", "FAQ"].map((item) => (
                <li key={item}>
                  <a href="#" className="text-gray-400 text-sm hover:text-white transition">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Col 3 - My Account */}
          <div className="lg:px-10">
            <h3 className="font-bold text-sm uppercase tracking-wider mb-5">
              My Account
            </h3>
            <ul className="space-y-3">
              {["My Profile", "Order History", "Wishlist", "Addresses", "Logout"].map((item) => (
                <li key={item}>
                  <a href="#" className="text-gray-400 text-sm hover:text-white transition">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Col 4 - Information */}
          <div className="lg:px-10">
            <h3 className="font-bold text-sm uppercase tracking-wider mb-5">
              Information
            </h3>
            <ul className="space-y-3">
              {["About Us", "Terms & Conditions", "Privacy Policy", "Terms of Use"].map((item) => (
                <li key={item}>
                  <a href="#" className="text-gray-400 text-sm hover:text-white transition">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Col 5 - Newsletter */}
          <div className="lg:pl-10 flex-1 sm:col-span-2 lg:col-span-1">
            <h3 className="font-bold text-sm uppercase tracking-wider mb-5">
              Newsletter
            </h3>
            <p className="text-gray-400 text-sm leading-relaxed mb-5">
              Subscribe to get updates on new products and exclusive offers.
            </p>
            <div className="flex w-full max-w-md">
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
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-gray-500 text-xs text-center sm:text-left">
            © 2024 BikeExpress. All Rights Reserved.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-5">
            <SiVisa size={38} className="text-white" />
            <SiMastercard size={30} className="text-yellow-400" />
            <span className="font-bold text-sm tracking-wide">
              <span className="text-green-400">e</span>
              <span className="text-white">asypaisa</span>
            </span>
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
