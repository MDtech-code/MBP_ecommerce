import Header from "../../header/ui/Header";
import Footer from "../../footer/ui/Footer";


export default function MainLayout({children}){
return (
<div className="min-h-screen bg-white  ">
<Header/>
<main>
{children}
</main>
<Footer/>
</div>
)

}