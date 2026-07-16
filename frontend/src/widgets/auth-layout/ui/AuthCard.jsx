export default function AuthCard({
  children
}) {

  return (

    <div
      className="
        bg-white
        rounded-3xl
        shadow-2xl
        px-10
        py-12
        max-w-md
        w-full
      "
    >

      {children}

    </div>

  );

}