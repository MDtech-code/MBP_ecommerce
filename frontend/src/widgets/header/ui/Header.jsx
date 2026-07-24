import TopBar from "./TopBar";
import MainNavbar from "./MainNavbar";
import { useAuthStore } from "@entities/user"
export default function Header(){
    const user = useAuthStore((state) => state.user)
return (
<header>
 {!user && <TopBar />}
     <MainNavbar user={user} />
</header>
)
}