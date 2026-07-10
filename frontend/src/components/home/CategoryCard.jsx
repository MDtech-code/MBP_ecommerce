export default function CategoryCard({ category }) {
  return (
    <div className="
      min-w-[140px] sm:min-w-[160px] md:min-w-[180px]
      flex flex-col items-center justify-center
      py-4 px-3
      border-r border-gray-200
    ">
      <img
        src={category.image}
        alt={category.name}
        className="h-14 sm:h-16 object-contain mb-3"
      />

      <h3 className="font-bold text-xs sm:text-sm text-gray-900 text-center">
        {category.name}
      </h3>

      <p className="text-xs text-gray-500 mt-1">
        {category.products}
      </p>
    </div>
  );
}
// export default function CategoryCard({
//   category
// }) {

//   return (

//     <div
//       className=" 
//         min-w-37.5
//         flex
//         flex-col
//         items-center
//         justify-center
//         py-4
//         border-r
//         border-gray-200
//       "
//     >

//       <img
//         src={category.image}
//         alt={category.name}
//         className="
//           h-16
//           object-contain
//           mb-3
//         "
//       />


//       <h3
//         className="
//           font-bold
//           text-sm
//           text-gray-900
//           text-center
//         "
//       >

//         {category.name}

//       </h3>


//       <p
//         className="
//           text-xs
//           text-gray-500
//           mt-1
//         "
//       >

//         {category.products}

//       </p>


//     </div>

//   );

// }