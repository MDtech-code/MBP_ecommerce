

import { SecurityGrid } from "@widgets/security"
export default function Security() {

  return (

    <>

      <div className="space-y-8">

        <div>

          <h1
            className="
              text-3xl
              font-extrabold
              text-gray-900
            "
          >
            Security Settings
          </h1>

          <p className="mt-2 text-gray-500">

            Manage your account security and login preferences.

          </p>

        </div>

        <SecurityGrid />

      </div>

    </>

  );

}