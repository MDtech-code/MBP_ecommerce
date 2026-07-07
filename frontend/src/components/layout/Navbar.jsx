import TopBar from "./TopBar";
import MainNavbar from "./MainNavbar";
import { useAuthStore } from "../../stores/authStore";
export default function Navbar(){
    const user = useAuthStore((state) => state.user)
return (
<header className="border border-yellow-500">
 {!user && <TopBar />}
     <MainNavbar user={user} />
</header>
)
}