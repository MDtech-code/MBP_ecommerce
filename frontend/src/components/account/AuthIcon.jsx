export default function AuthIcon({
  icon: Icon,
  badge
}) {


return (

<div
className="
relative
mx-auto
w-24
h-24
rounded-full
bg-gray-100
flex
items-center
justify-center
"
>


<Icon
size={45}
className="text-gray-700"
/>



<div
className="
absolute
right-1
bottom-1
w-8
h-8
rounded-full
bg-primary
text-white
flex
items-center
justify-center
font-bold
"
>

{badge}

</div>


</div>


)

}