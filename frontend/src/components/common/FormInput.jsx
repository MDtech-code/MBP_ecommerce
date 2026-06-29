import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";


export default function FormInput({
  icon: Icon,
  type = "text",
  placeholder,
  value,
  onChange,
}) {


  const [showPassword, setShowPassword] = useState(false);


  const isPassword = type === "password";


  return (

    <div
      className="
        flex
        items-center
        gap-3
        border
        border-gray-200
        rounded-lg
        px-4
        py-3
        focus-within:border-primary
      "
    >


      {
        Icon && (

          <Icon
            size={20}
            className="text-gray-400 shrink-0"
          />

        )
      }



      <input

        type={
          isPassword && showPassword
            ? "text"
            : type
        }

        placeholder={placeholder}

        value={value}

        onChange={onChange}

        className="
          w-full
          outline-none
          text-gray-900
        "

      />



      {
        isPassword && (

          <button
            type="button"
            onClick={() =>
              setShowPassword(!showPassword)
            }
          >

            {
              showPassword

              ?

              <EyeOff
                size={20}
                className="text-gray-400"
              />

              :

              <Eye
                size={20}
                className="text-gray-400"
              />

            }

          </button>

        )
      }



    </div>

  );

}