import {
  ShieldCheck,
  WalletCards,
  Truck,
  RotateCcw,
} from "lucide-react";


const benefits = [
  {
    id: 1,
    title: "100% Original Products",
    icon: ShieldCheck,
  },
  {
    id: 2,
    title: "Cash on Delivery",
    icon: WalletCards,
  },
  {
    id: 3,
    title: "Nationwide Delivery",
    icon: Truck,
  },
  {
    id: 4,
    title: "7 Days Easy Returns",
    icon: RotateCcw,
  },
];

export default function HeroBenefits() {
  return (
    <div className="flex flex-wrap mt-10 ml-1 divide-x divide-gray-600">
      {benefits.map(({ id, title, icon: Icon }) => (
        <div
          key={id}
          className="relative flex items-center gap-1 px-2 text-white"
        >
          <Icon size={28} className=" text-white shrink-0" />
          <span className="absolute  left-5 bottom-4 text-primary mx-2 ">
                •
              </span>
          <span className="text-sm font-semibold wrap-break-word whitespace-normal leading-tight max-w-25">
            {title}
          </span>
        </div>
      ))}
    </div>
  );
}


// export default function HeroBenefits() {

//   return (

//     <div className="flex flex-wrap  mt-10 ml-1">

//       {
//         benefits.map(({ id, title, icon: Icon }) => (

//           <div
//             key={id}
//             className="
//               flex
//               items-center
//               text-white
//             "
//           >

//             <Icon
//               size={28}
//               className="text-white"
//             />


//             <span
//               className="
//                 text-sm
//                 font-semibold
//                 max-w-30
//               "
//             >
//               {title}
//             </span>


//           </div>

//         ))
//       }


//     </div>

//   );

// }