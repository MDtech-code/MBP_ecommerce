import { Header } from "@widgets/header"
import { Footer } from "@widgets/footer"


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