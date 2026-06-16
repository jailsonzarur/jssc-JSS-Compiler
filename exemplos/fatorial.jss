function int fatorial(int fat) {
    if (fat > 1) {
        return fat * fatorial(fat - 1);
    } else {
        return 1;
    }
}

function void main() {
    let int numero;
    console.log("Programa Fatorial. Digite o valor:");
    input(numero);
    console.log(fatorial(numero));
}
