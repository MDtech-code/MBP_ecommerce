import { FcGoogle } from "react-icons/fc";
import { FaFacebookF } from "react-icons/fa";

export default function SocialLogin() {
  return (
    <div className="mt-6">
      {/* Divider */}
      <div className="flex items-center gap-3 text-gray-400 text-sm">
        <span className="h-px bg-gray-200 flex-1" />
        OR CONTINUE WITH
        <span className="h-px bg-gray-200 flex-1" />
      </div>

      {/* Social buttons with required icon */}
      <div className="grid grid-cols-2 gap-3 mt-5">
        <button className="flex items-center justify-center gap-2 border rounded-lg py-3 font-semibold">
        <FcGoogle size={20} />
          Google
        </button>

        <button className="flex items-center justify-center gap-2 border rounded-lg py-3 font-semibold">
          <FaFacebookF size={20}/>
          Facebook
        </button>
      </div>
    </div>
  );
}
