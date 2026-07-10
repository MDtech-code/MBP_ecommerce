import TopBar from "./TopBar";
import MainNavbar from "./MainNavbar";
import { useAuthStore } from "../../stores/authStore";
export default function Navbar(){
    const user = useAuthStore((state) => state.user)
    console.log(`mia navbar sa console ara hu ya user ha ${user}`)
return (
<header>
 {!user && <TopBar />}
     <MainNavbar user={user} />
</header>
)
}