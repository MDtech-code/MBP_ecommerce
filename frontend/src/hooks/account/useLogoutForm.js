
import { useLogout } from "./useAuthMutations";
import { useNavigate } from "react-router-dom";



export function useLogoutForm() {
    const navigate = useNavigate();
    const {mutate:logout, isPending} =useLogout()

    const handleLogout = () => {
      logout(undefined, {
        onSuccess: () => navigate("/login"),
        onError: () => navigate("/login"),
      });
    };

    return {
        isPending,
        handleLogout
    }


}