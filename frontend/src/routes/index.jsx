import {createBrowserRouter} from "react-router-dom";
import Home from "../pages/Home";
import TestintegrationPage from '../pages/TestIntegrationPage'


export const router=createBrowserRouter([
{
 path:"/",
 element:<Home/>
},
{
    path:'/testapp',
    element:<TestintegrationPage/>
}

])