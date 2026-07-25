// src/app/layouts/MainLayout.jsx

import { Outlet } from "react-router-dom"
import { Header } from "@widgets/header"
import { Footer } from "@widgets/footer"

export default function MainLayout() {
  return (
    <div className="min-h-screen bg-surface">
      <Header />
      <main>
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
// import { Header } from "@widgets/header"
// import { Footer } from "@widgets/footer"


// export default function MainLayout({children}){
// return (
// <div className="min-h-screen bg-white  ">
// <Header/>
// <main>
// {children}
// </main>
// <Footer/>
// </div>
// )

// }