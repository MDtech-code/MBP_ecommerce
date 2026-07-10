import Header from "./Header";
import Footer from "./Footer";


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