// widgets/auth/AuthBrand.jsx

export default function AuthBrand({
  title = "",
  highlight = "",
  description = "",
}) {
  return (
    <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
      <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black italic leading-none tracking-tight text-gray-900 dark:text-white lg:text-white">
        {title}
        <br />
        <span className="text-primary mt-1 inline-block">
          {highlight}
        </span>
      </h1>

      <p className="mt-3 sm:mt-5 text-sm sm:text-base lg:text-lg max-w-70 sm:max-w-sm lg:max-w-md text-gray-600 dark:text-gray-400 lg:text-gray-200">
        {description}
      </p>

    </div>
  );
}
