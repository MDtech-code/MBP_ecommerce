// widgets/auth/AuthBrand.jsx

export default function AuthBrand({
  title = "WELCOME BACK",
  highlight = "RIDER!",
  description = "Login to your account and continue your journey with BikeExpress.",
}) {
  return (
    <div className="flex flex-col items-center text-center lg:items-start lg:text-left">

      {/* ── OLD ──────────────────────────────────────────────────────
      <h1
        className="
          text-3xl sm:text-4xl lg:text-5xl
          font-black
          italic
          text-gray-900 dark:text-white lg:text-white lg:dark:text-white
          leading-none tracking-tight
        "
      >
        {title}
        <br className="block" />
        <span className="text-primary mt-1 inline-block">
          {highlight}
        </span>
      </h1>
      ─────────────────────────────────────────────────────────────── */}

      {/* ── NEW ──────────────────────────────────────────────────────
          lg:dark:text-white removed — lg:text-white already covers
          both light and dark on desktop. The extra variant was
          overriding to the same value, pure redundancy.

          className="block" removed from <br> — <br> is a void
          element that creates a line break by its own nature.
          A className on it does absolutely nothing.
      ─────────────────────────────────────────────────────────────── */}
      <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black italic leading-none tracking-tight text-gray-900 dark:text-white lg:text-white">
        {title}
        <br />
        <span className="text-primary mt-1 inline-block">
          {highlight}
        </span>
      </h1>

      {/* ── OLD ──────────────────────────────────────────────────────
      <p
        className="
          mt-3 sm:mt-5
          text-sm sm:text-base lg:text-lg
          max-w-70 sm:max-w-sm lg:max-w-md
          text-gray-600 dark:text-gray-400 lg:text-gray-200 lg:dark:text-gray-200
        "
      >
        {description}
      </p>
      ─────────────────────────────────────────────────────────────── */}

      {/* ── NEW ──────────────────────────────────────────────────────
          lg:dark:text-gray-200 removed — same redundancy as above.
          lg:text-gray-200 already covers desktop in both color modes
          since the text sits on the dark image background regardless
          of the user's dark mode preference.
          Class string flattened from multiline fragment to single line
          — same breakpoint logic, easier to scan.
      ─────────────────────────────────────────────────────────────── */}
      <p className="mt-3 sm:mt-5 text-sm sm:text-base lg:text-lg max-w-70 sm:max-w-sm lg:max-w-md text-gray-600 dark:text-gray-400 lg:text-gray-200">
        {description}
      </p>

    </div>
  );
}
// export default function AuthBrand({
//   title = "WELCOME BACK",
//   highlight = "RIDER!",
//   description = "Login to your account and continue your journey with BikeExpress."
// }) {
//   return (
//     <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
//       <h1
//         className="
//           text-3xl sm:text-4xl lg:text-5xl 
//           font-black
//           italic
//           text-gray-900 dark:text-white lg:text-white lg:dark:text-white
//           leading-none tracking-tight
//         "
//       >
//         {title}
//         <br className="block" />
//         <span className="text-primary mt-1 inline-block">
//           {highlight}
//         </span>
//       </h1>

//       <p
//         className="
//           mt-3 sm:mt-5
//           text-sm sm:text-base lg:text-lg
//           max-w-70 sm:max-w-sm lg:max-w-md
//           text-gray-600 dark:text-gray-400 lg:text-gray-200 lg:dark:text-gray-200
//         "
//       >
//         {description}
//       </p>
//     </div>
//   )
// }
