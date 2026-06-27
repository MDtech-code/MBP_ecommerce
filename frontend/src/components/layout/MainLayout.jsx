import Navbar from "./Navbar";
import Footer from "./Footer";


export default function MainLayout({children}){
return (
<div className="min-h-screen bg-white">
<Navbar/>
<main>
{children}
</main>
<Footer/>
</div>
)

}