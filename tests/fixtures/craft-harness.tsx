import React from "react";
import { createRoot } from "react-dom/client";
import { ProductDataProvider } from "../../src/context/ProductDataContext";
import { CraftStudio } from "../../src/studios/craft/CraftStudio";
import { DepartmentStudio } from "../../src/studios/department/DepartmentStudio";

const host = document.getElementById("root")!;
const validationPath = "/__craft-validation";
const validationProps = window.location.pathname === validationPath ? {
  pathname: "/content/draft/edit",
  search: window.location.search,
  navigate: (destination: string) => {
    const url = new URL(destination, window.location.origin);
    url.pathname = validationPath;
    window.location.assign(url.href);
  },
} : {};
createRoot(host).render(<ProductDataProvider>{new URLSearchParams(window.location.search).has("department") ? <DepartmentStudio /> : <CraftStudio {...validationProps} />}</ProductDataProvider>);
