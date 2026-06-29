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
// export default function AuthBrand(){


// return (

// <div>


// <h1
// className="
// text-5xl
// font-black
// italic
// text-white
// "
// >

// WELCOME BACK

// <br/>

// <span className="text-primary">

// RIDER!

// </span>


// </h1>



// <p
// className="
// mt-5
// text-gray-200
// text-lg
// max-w-md
// "
// >

// Login to your account and continue
// your journey with BikeExpress.

// </p>


// </div>

// )

// }

// export default function AuthBrand() {

//   return (

//     <div className="
//       text-white
//       max-w-md
//     ">


//       <h1 className="
//         text-5xl
//         font-black
//         italic
//         leading-tight
//       ">

//         Ride Better.

//         <br />

//         <span className="text-primary">
//           Choose Genuine Parts.
//         </span>

//       </h1>



//       <p className="
//         mt-5
//         text-gray-300
//         text-lg
//       ">

//         Manage your orders, track deliveries,
//         and get the best motorcycle parts
//         across Pakistan.

//       </p>


//       <div className="
//         mt-8
//         flex
//         gap-4
//         text-sm
//         text-gray-300
//       ">

//         <span>
//           ✓ Original Parts
//         </span>

//         <span>
//           ✓ Fast Delivery
//         </span>

//       </div>


//     </div>

//   );

// }