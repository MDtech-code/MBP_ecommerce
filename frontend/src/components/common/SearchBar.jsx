// // src/components/common/SearchBar.jsx
// import { useState, useRef, useEffect } from "react"
// import { Search, X } from "lucide-react"

// export default function SearchBar({ variant = "full" }) {
//   const [open, setOpen] = useState(false)
//   const ref = useRef(null)

//   useEffect(() => {
//     function handleClickOutside(e) {
//       if (ref.current && !ref.current.contains(e.target)) {
//         setOpen(false)
//       }
//     }
//     if (open) document.addEventListener("mousedown", handleClickOutside)
//     return () => document.removeEventListener("mousedown", handleClickOutside)
//   }, [open])

//   // Full bar — used on xl screens
//   if (variant === "full") {
//     return (
//       <div className="flex h-11 flex-1 max-w-sm items-center border rounded-full overflow-hidden">
//         <input
//           type="text"
//           placeholder="Search parts or bike model..."
//           className="flex-1 px-4 text-sm outline-none"
//         />
//         <button className="bg-primary text-white px-4 h-full flex items-center justify-center">
//           <Search size={17} />
//         </button>
//       </div>
//     )
//   }

//   // Icon with floating box — used below xl
//   return (
//     <div className="relative" ref={ref}>
//       <button
//         onClick={() => setOpen((prev) => !prev)}
//         className="p-2 rounded-full hover:bg-gray-100 transition-colors"
//       >
//         {open ? <X size={20} /> : <Search size={20} />}
//       </button>

//       {open && (
//         <div className="absolute top-12 right-0 w-72 bg-white border
//                         rounded-xl shadow-lg overflow-hidden z-50
//                         flex items-center">
//           <input
//             autoFocus
//             type="text"
//             placeholder="Search parts or bike model..."
//             className="flex-1 px-4 py-2.5 text-sm outline-none"
//           />
//           <button className="bg-primary text-white px-4 py-3.5 flex items-center">
//             <Search size={16} />
//           </button>
//         </div>
//       )}
//     </div>
//   )
// }