export default function AuthBrand({
  title = "WELCOME BACK",
  highlight = "RIDER!",
  description = "Login to your account and continue your journey with BikeExpress."
}) {
  return (
    <div>
      <h1
        className="
          text-5xl
          font-black
          italic
          text-white
        "
      >
        {title}
        <br />
        <span className="text-primary">
          {highlight}
        </span>
      </h1>

      <p
        className="
          mt-5
          text-gray-200
          text-lg
          max-w-md
        "
      >
        {description}
      </p>
    </div>
  )
}
