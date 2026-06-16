function real media(real n1, real n2) {
    return (n1 + n2) / 2;
}

function void printMedia(real v1, real v2) {
    const real x = media(v1, v2);
    console.log("Resultado: ", x);
}

function void main() {
    let real n1;
    let real n2;
    console.log("Programa Media. Digite os valores:");
    input(n1, n2);
    printMedia(n1, n2);
}
