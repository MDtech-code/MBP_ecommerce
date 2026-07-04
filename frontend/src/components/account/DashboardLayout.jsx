import AccountHeader from "./AccountHeader";
import AccountSidebar from "./AccountSidebar";

export default function DashboardLayout({ children }) {
  return (
    <div className="min-h-screen bg-surface">
      {/* Top Header */}
      <AccountHeader />

      <div className="flex min-h-[calc(100vh-80px)]">
        {/* Sidebar */}
        <AccountSidebar />

        {/* Content */}
        <main className="flex-1 p-6 lg:p-10">{children}</main>
      </div>
    </div>
  );
}

// import AccountHeader from "./AccountHeader";
// import AccountSidebar from "./AccountSidebar";


// export default function DashboardLayout({
//   children
// }) {


//   return (

//     <div
//       className="
//         min-h-screen
//         bg-surface
//       "
//     >


//       {/* Top Header */}

//       <AccountHeader />



//       <div
//         className="
//           flex
//           min-h-[calc(100vh-80px)]
//         "
//       >


//         {/* Sidebar */}

//         <AccountSidebar />




//         {/* Content */}

//         <main
//           className="
//             flex-1
//             p-6
//             lg:p-10
//           "
//         >

//           {children}

//         </main>



//       </div>


//     </div>

//   );

// }