export default function Logo(){

  return (
    <div className="flex items-center gap-2">
      <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white font-black">B</div>
      <div>
        <h1 className="font-black text-xl leading-none">BIKE<span className="text-primary">XPRESS</span></h1>
        <p className="text-xs text-muted">Quality Parts. Smooth Rides.</p>
      </div>
    </div>
  )
}